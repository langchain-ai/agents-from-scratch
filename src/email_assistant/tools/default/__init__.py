"""Default tools for email assistant."""

from email_assistant.tools.default.email_tools import write_email, triage_email, Done
from email_assistant.tools.default.calendar_tools import schedule_meeting, check_calendar_availability
from email_assistant.tools.default.prompt_templates import (
    STANDARD_TOOLS_PROMPT,
    AGENT_TOOLS_PROMPT,
    HITL_TOOLS_PROMPT,
    HITL_MEMORY_TOOLS_PROMPT
)

__all__ = [
    "write_email",
    "triage_email",
    "Done",
    "schedule_meeting", 
    "check_calendar_availability",
    "STANDARD_TOOLS_PROMPT",
    "AGENT_TOOLS_PROMPT",
    "HITL_TOOLS_PROMPT",
    "HITL_MEMORY_TOOLS_PROMPT"
]