#!/usr/bin/env python
from langchain_core.messages import AIMessage
from langgraph.graph import END

from email_assistant.email_assistant import should_continue


def test_should_continue_no_tool_calls():
    """Verify that an AI message without tool calls returns END."""
    state = {"messages": [AIMessage(content="I have processed your request.")]}
    assert should_continue(state) == END


def test_should_continue_empty_tool_calls_list():
    """Verify that an AI message with an empty tool-call list returns END."""
    state = {"messages": [AIMessage(content="", tool_calls=[])]}
    assert should_continue(state) == END


def test_should_continue_ordinary_tool_call():
    """Verify that an ordinary tool call returns Action."""
    tool_call = {
        "name": "write_email",
        "args": {"to": "test@example.com", "subject": "Meeting", "content": "Hello"},
        "id": "call_1",
    }
    state = {"messages": [AIMessage(content="", tool_calls=[tool_call])]}
    assert should_continue(state) == "Action"


def test_should_continue_done_tool():
    """Verify that a Done tool call returns END."""
    tool_call = {
        "name": "Done",
        "args": {},
        "id": "call_2",
    }
    state = {"messages": [AIMessage(content="", tool_calls=[tool_call])]}
    assert should_continue(state) == END
