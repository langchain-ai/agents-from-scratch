"""Tool failures in the email assistant's tool node (no model or API calls)."""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "placeholder")  # the module builds a client at import

from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.tools import ToolException, tool  # noqa: E402

import email_assistant.email_assistant as ea  # noqa: E402


@tool
def check_calendar_availability(day: str) -> str:
    """Check calendar availability for a given day."""
    raise TimeoutError("calendar service timed out")


@tool
def schedule_meeting(subject: str) -> str:
    """Schedule a meeting."""
    raise ToolException("calendar API returned 503")


@tool
def buggy_tool(day: str) -> str:
    """A tool with a programming error."""
    return {}["missing"]


@pytest.fixture
def tools(monkeypatch):
    patched = {
        **ea.tools_by_name,
        "check_calendar_availability": check_calendar_availability,
        "schedule_meeting": schedule_meeting,
        "buggy_tool": buggy_tool,
    }
    monkeypatch.setattr(ea, "tools_by_name", patched)


def run(*calls):
    state = {"messages": [AIMessage(content="", tool_calls=list(calls))]}
    return ea.tool_node(state)["messages"]


def call(name, args, call_id):
    return {"name": name, "args": args, "id": call_id}


@pytest.mark.parametrize(
    "name,args,error",
    [
        ("check_calendar_availability", {"day": "Tuesday"}, "TimeoutError"),
        ("schedule_meeting", {"subject": "Sync"}, "ToolException"),
    ],
)
def test_tool_failure_is_returned_to_the_model(tools, name, args, error):
    (message,) = run(call(name, args, "call_1"))
    assert message["tool_call_id"] == "call_1"
    assert message["content"].startswith(f"Error: {error}")


def test_each_result_keeps_its_tool_call_id(tools):
    messages = run(
        call("check_calendar_availability", {"day": "Tuesday"}, "call_1"),
        call("write_email", {"to": "a@example.com", "subject": "Hi", "content": "Hello"}, "call_2"),
    )
    assert [m["tool_call_id"] for m in messages] == ["call_1", "call_2"]
    assert messages[0]["content"].startswith("Error: TimeoutError")
    assert messages[1]["content"].startswith("Email sent to a@example.com")


def test_programming_errors_still_raise(tools):
    with pytest.raises(KeyError):
        run(call("buggy_tool", {"day": "Tuesday"}, "call_1"))
