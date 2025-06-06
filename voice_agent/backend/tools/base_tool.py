from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseTool(ABC):
    """
    Base class for all tools used by the MediFox healthcare agent.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def run(self, args: Dict[str, Any], context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Execute the tool with the given arguments.
        
        Args:
            args: The arguments for the tool
            context: The current conversation context
            
        Returns:
            Dictionary containing the tool's response
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Returns the schema for this tool in a format suitable for OpenAI's function calling.
        Override this method in specific tools to provide custom schemas.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
