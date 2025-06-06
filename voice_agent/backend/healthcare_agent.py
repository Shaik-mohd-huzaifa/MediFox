import os
import json
from typing import Dict, List, Any, Optional, Tuple
import httpx

from memory_manager import MemoryManager
from tool_manager import ToolManager


class HealthcareAgent:
    """
    The MediFox Healthcare Agent serves as an intermediary between healthcare providers and patients.
    It processes natural language inputs, uses tools for specific tasks, maintains memory,
    and generates appropriate responses.
    """
    
    def __init__(self):
        """Initialize the healthcare agent with tools and memory management."""
        self.tool_manager = ToolManager()
        self.memory_manager = MemoryManager()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Load the agent system prompt
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt for the healthcare agent."""
        prompt = """You are MediFox, an advanced healthcare virtual assistant designed to help bridge communication between healthcare providers and patients.

Your primary responsibilities include:
1. Gathering and maintaining accurate patient information
2. Conducting preliminary health assessments
3. Managing medication information and providing reminders
4. Handling appointment scheduling and follow-ups
5. Providing reliable health information from trusted medical sources
6. Summarizing patient data for healthcare providers

IMPORTANT GUIDELINES:
- Always maintain a professional, compassionate, and helpful tone
- Prioritize patient safety and well-being above all else
- Never provide definitive medical diagnoses; instead, suggest possibilities and refer to healthcare providers
- Handle patient data with strict confidentiality and respect for privacy
- Clearly distinguish between evidence-based medical information and general advice
- For urgent medical situations, immediately advise seeking emergency care
- If you don't know something or are uncertain, acknowledge limitations and avoid speculation
- Ask for any missing patient information that would be important for assessment
- When information is incomplete, make this clear and note what additional data would be helpful

You have access to various tools to help you perform these functions effectively. Use them as needed to provide the best assistance possible.

Remember that your role is to support healthcare decisions, not replace the judgment of licensed medical professionals.
"""
        return prompt
    
    async def process_input(
        self, 
        user_input: str, 
        session_id: str, 
        patient_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process user input, execute tools as needed, and generate a response.
        
        Args:
            user_input: The user's input text
            session_id: The current session ID
            patient_id: Optional patient ID if available
            
        Returns:
            Tuple containing agent response and metadata
        """
        # Load conversation context from memory
        context = self.memory_manager.load_conversation(session_id)
        
        # If this is a new conversation, add the system prompt
        if not context:
            context.append({"role": "system", "content": self.system_prompt})
        
        # If patient_id is available, add patient context summary
        if patient_id:
            patient_context = self.memory_manager.summarize_patient_context(patient_id)
            if patient_context and not any("patient context summary" in msg.get("content", "") for msg in context):
                context.append({"role": "system", "content": f"Current patient context summary:\n{patient_context}"})
        
        # Add user input to context
        context.append({"role": "user", "content": user_input})
        
        # Get agent response using OpenAI API with tool calling
        response_content, metadata = await self._get_llm_response(context)
        
        # Add agent response to context
        context.append({"role": "assistant", "content": response_content})
        
        # Save updated context to memory
        self.memory_manager.save_conversation(session_id, context)
        
        return response_content, metadata
    
    async def _get_llm_response(
        self, 
        context: List[Dict[str, str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Get response from LLM with tool calling capability.
        
        Args:
            context: The conversation context
            
        Returns:
            Tuple containing response content and metadata including tool calls
        """
        # Get tool schemas
        tool_schemas = self.tool_manager.get_tool_schemas()
        
        # Prepare the API request
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o",
            "messages": context,
            "tools": tool_schemas,
            "tool_choice": "auto"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            result = response.json()
            
            if "error" in result:
                return f"Error: {result['error']['message']}", {"error": result["error"]}
            
            # Check for tool calls
            message = result["choices"][0]["message"]
            response_content = message.get("content") or ""
            
            metadata = {
                "finish_reason": result["choices"][0]["finish_reason"],
                "model": result.get("model", "gpt-4o")
            }
            
            # If tool calls are present, execute them
            if "tool_calls" in message:
                metadata["tool_calls"] = message["tool_calls"]
                tool_results = await self.tool_manager.parse_and_execute_tool_calls(
                    message["tool_calls"], context
                )
                metadata["tool_results"] = tool_results
                
                # Add tool call results to context and get follow-up response
                tool_messages = []
                for tc, tr in zip(message["tool_calls"], tool_results):
                    tool_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tc]
                    })
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(tr)
                    })
                
                # Get follow-up response after tool execution
                if tool_messages:
                    new_context = context + tool_messages
                    follow_up_response = await self._get_follow_up_response(new_context)
                    metadata["follow_up_response"] = follow_up_response
                    response_content = follow_up_response.get("content", response_content)
        
        return response_content, metadata
    
    async def _get_follow_up_response(
        self, 
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get a follow-up response after tool execution.
        
        Args:
            context: Updated conversation context with tool results
            
        Returns:
            Response message from LLM
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o",
            "messages": context
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            result = response.json()
            
            if "error" in result:
                return {"content": f"Error: {result['error']['message']}"}
            
            return result["choices"][0]["message"]
