from typing import Dict, List, Any, Optional
import asyncio
import json

from tools import (
    PatientInfoTool,
    MedicalHistoryTool,
    SymptomAssessmentTool,
    MedicationManagementTool,
    AppointmentSchedulingTool,
    HealthcareProviderLookupTool,
    MedicalReferenceDBTool
)


class ToolManager:
    """
    Manages the tools available to the MediFox healthcare agent.
    Provides registration, schema generation, and execution functions.
    """
    
    def __init__(self):
        """Initialize the tool manager and register all available tools."""
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register all the default healthcare tools."""
        self.register_tool(PatientInfoTool())
        self.register_tool(MedicalHistoryTool())
        self.register_tool(SymptomAssessmentTool())
        self.register_tool(MedicationManagementTool())
        self.register_tool(AppointmentSchedulingTool())
        self.register_tool(HealthcareProviderLookupTool())
        self.register_tool(MedicalReferenceDBTool())
    
    def register_tool(self, tool) -> None:
        """
        Register a tool with the manager.
        
        Args:
            tool: The tool instance to register
        """
        self.tools[tool.name] = tool
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get schema definitions for all registered tools.
        
        Returns:
            List of tool schemas in OpenAI function format
        """
        return [tool.get_schema() for tool in self.tools.values()]
    
    async def execute_tool(
        self, 
        tool_name: str, 
        args: Dict[str, Any], 
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Execute a specified tool with the provided arguments.
        
        Args:
            tool_name: Name of the tool to execute
            args: Arguments to pass to the tool
            context: Optional conversation context
            
        Returns:
            Dictionary with the tool's result
        """
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found"}
        
        try:
            tool = self.tools[tool_name]
            result = await tool.run(args, context)
            return result
        except Exception as e:
            return {
                "error": f"Tool execution failed: {str(e)}",
                "tool": tool_name,
                "args": args
            }
    
    async def parse_and_execute_tool_calls(
        self, 
        tool_calls: List[Dict[str, Any]], 
        context: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse and execute multiple tool calls from LLM output.
        
        Args:
            tool_calls: List of tool calls from LLM
            context: Optional conversation context
            
        Returns:
            List of results from each tool execution
        """
        results = []
        
        for call in tool_calls:
            function_name = call.get("function", {}).get("name")
            function_args = call.get("function", {}).get("arguments", "{}")
            
            # Parse arguments
            try:
                args = json.loads(function_args)
            except json.JSONDecodeError:
                results.append({
                    "error": "Failed to parse function arguments",
                    "tool": function_name,
                    "args_string": function_args
                })
                continue
                
            # Execute the tool
            result = await self.execute_tool(function_name, args, context)
            
            # Add metadata to the result
            result["tool_name"] = function_name
            result["tool_call_id"] = call.get("id")
            
            results.append(result)
        
        return results
