from typing import Dict, List, Callable, Any
from langchain_core.tools import BaseTool

def get_tools(tool_names: List[str] = None, include_gmail: bool = False) -> List[BaseTool]:
    """Get specified tools or all tools if tool_names is None.
    
    Args:
        tool_names: Optional list of tool names to include. If None, returns all tools.
        include_gmail: Whether to include Gmail tools. Defaults to False.
        
    Returns:
        List of tool objects
    """
    # Import default tools
    from email_assistant.tools.default.email_tools import write_email, Done, Question
    from email_assistant.tools.default.calendar_tools import schedule_meeting, check_calendar_availability
    
    # Base tools dictionary
    all_tools = {
        "write_email": write_email,
        "Done": Done,
        "Question": Question,
        "schedule_meeting": schedule_meeting,
        "check_calendar_availability": check_calendar_availability,
    }
    
    # Add Gmail tools if requested
    if include_gmail:
        try:
            from email_assistant.tools.gmail.gmail_tools import (
                fetch_emails_tool,
                send_email_tool,
                check_calendar_tool,
                schedule_meeting_tool
            )
            
            all_tools.update({
                "fetch_emails_tool": fetch_emails_tool,
                "send_email_tool": send_email_tool,
                "check_calendar_tool": check_calendar_tool,
                "schedule_meeting_tool": schedule_meeting_tool,
            })
        except ImportError:
            # If Gmail tools aren't available, continue without them
            pass
    
    if tool_names is None:
        return list(all_tools.values())
    
    return [all_tools[name] for name in tool_names if name in all_tools]

def get_tools_by_name(tools: List[BaseTool] = None) -> Dict[str, BaseTool]:
    """Get a dictionary of tools mapped by name."""
    if tools is None:
        tools = get_tools()
    
    return {tool.name: tool for tool in tools}
