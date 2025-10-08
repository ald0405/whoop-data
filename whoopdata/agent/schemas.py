"""Agent schemas for state and context management."""

from typing import Annotated, List, Any, Dict
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from dataclasses import dataclass


# Agent State Schema
class HealthAgentState(TypedDict, total=False):
    """State schema for the health data agent."""
    messages: Annotated[List[AnyMessage], add_messages]
    user_id: str
    health_data: Dict[str, Any]  # Store retrieved health data
    insights: str  # Generated insights from health data


# Runtime Context Schema  
@dataclass
class HealthContextSchema:
    """Runtime context for health data operations."""
    user_id: str = "default_user"
    health_api_base_url: str = "http://localhost:8000"
    preferred_data_range_days: int = 30
    
    def __post_init__(self):
        """Initialize any additional context data."""
        pass


# Configuration Schema
@dataclass  
class AgentConfig:
    """Configuration for LangGraph agent."""
    thread_id: str
    recursion_limit: int = 10
    
    def to_dict(self) -> Dict:
        """Convert to LangGraph config format."""
        return {
            "configurable": {"thread_id": self.thread_id},
            "recursion_limit": self.recursion_limit,
        }