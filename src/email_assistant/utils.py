from langchain_core.messages import convert_to_openai_messages
from langgraph.prebuilt.interrupt import HumanInterruptConfig
from langchain_core.tools import BaseTool
from langchain_core.tools import tool as create_tool
from langgraph.types import interrupt
from langchain_core.runnables import RunnableConfig
import json

def format_messages(messages):
    """Format a list of chat messages into a readable string format.
    
    Args:
        messages (List[ChatMessage]): A list of message dictionaries containing fields like 
            'role', 'content', etc. Each message should follow the ChatMessage format.
    
    Returns:
        str: A formatted string where each message is separated by === Message { } === blocks,
            with each field indented and displayed on a new line.
    """
    messages = convert_to_openai_messages(messages)
    formatted_output = ""
    
    for message in messages:
        # Get role and content
        role = message.get("role", "unknown").capitalize()
        content = message.get("content", "")
        
        # Create header with equal signs
        header = f" {role} Message "
        line = "=" * 32 + header + "=" * 32
        
        # Format message with header and content
        message_str = f"{line}\n\n{content}\n\n"
        formatted_output += message_str
    
    return formatted_output.strip()

def format_email_markdown(subject, author, to, email_thread):
    """Format email details into a nicely formatted markdown string for display"""
    return f"""# Original Email

**Subject**: {subject}
**From**: {author}
**To**: {to}

{email_thread}

---
"""

def format_for_display(state, tool_call):
    """Format content for display in Agent Inbox
    
    Args:
        state: Current message state
        tool_call: The tool call to format
    """
    # Initialize empty display
    display = ""
    
    # Add tool call information
    if tool_call["name"] == "write_email":
        display += f"""# Email Draft

**To**: {tool_call["args"].get("to")}
**Subject**: {tool_call["args"].get("subject")}

{tool_call["args"].get("content")}
"""
    elif tool_call["name"] == "schedule_meeting":
        display += f"""# Calendar Invite

**Meeting**: {tool_call["args"].get("subject")}
**Attendees**: {', '.join(tool_call["args"].get("attendees"))}
**Duration**: {tool_call["args"].get("duration_minutes")} minutes
**Day**: {tool_call["args"].get("preferred_day")}
"""
    elif tool_call["name"] == "Question":
        # Special formatting for questions to make them clear
        display += f"""# Question for User

{tool_call["args"].get("content")}
"""
    else:
        # Generic format for other tools
        display += f"""# Tool Call: {tool_call["name"]}

Arguments:
{json.dumps(tool_call["args"], indent=2)}
"""
    return display

def parse_email(email_input: dict) -> dict:
    """Parse an email input dictionary.

    Args:
        email_input (dict): Dictionary containing email fields:
            - author: Sender's name and email
            - to: Recipient's name and email
            - subject: Email subject line
            - email_thread: Full email content

    Returns:
        tuple[str, str, str, str]: Tuple containing:
            - author: Sender's name and email
            - to: Recipient's name and email
            - subject: Email subject line
            - email_thread: Full email content
    """
    return (
        email_input["author"],
        email_input["to"],
        email_input["subject"],
        email_input["email_thread"],
    )

def extract_message_content(message) -> str:
    """Extract content from different message types as clean string.
    
    Args:
        message: A message object (HumanMessage, AIMessage, ToolMessage)
        
    Returns:
        str: Extracted content as clean string
    """
    content = message.content
    
    # Check for recursion marker in string
    if isinstance(content, str) and '<Recursion on AIMessage with id=' in content:
        return "[Recursive content]"
    
    # Handle string content
    if isinstance(content, str):
        return content
        
    # Handle list content (AIMessage format)
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and 'text' in item:
                text_parts.append(item['text'])
        return "\n".join(text_parts)
    
    # Don't try to handle recursion to avoid infinite loops
    # Just return string representation instead
    return str(content)

def format_few_shot_examples(examples):
    """Format examples into a readable string representation.

    Args:
        examples (List[Item]): List of example items from the vector store, where each item
            contains a value string with the format:
            'Email: {...} Original routing: {...} Correct routing: {...}'

    Returns:
        str: A formatted string containing all examples, with each example formatted as:
            Example:
            Email: {email_details}
            Original Classification: {original_routing}
            Correct Classification: {correct_routing}
            ---
    """
    formatted = []
    for example in examples:
        # Parse the example value string into components
        email_part = example.value.split('Original routing:')[0].strip()
        original_routing = example.value.split('Original routing:')[1].split('Correct routing:')[0].strip()
        correct_routing = example.value.split('Correct routing:')[1].strip()
        
        # Format into clean string
        formatted_example = f"""Example:
Email: {email_part}
Original Classification: {original_routing}
Correct Classification: {correct_routing}
---"""
        formatted.append(formatted_example)
    
    return "\n".join(formatted)

def _get_tool_input_display_kwargs(tool_input, tool_call_schema):
    if isinstance(tool_call_schema, dict):
        allowed_keys = tool_call_schema["properties"]
    else:
        allowed_keys = tool_call_schema.model_json_schema()["properties"]

    return {key: tool_input[key] for key in allowed_keys}

def tool_with_human_in_the_loop(
    tool,
    *,
    tool_name: str = None,
    interrupt_config: HumanInterruptConfig,
    interrupt_description: str = None
):
    if not isinstance(tool, BaseTool):
        tool = create_tool(tool)

    if tool_name is None:
        tool_name = tool.name

    # propagate more kwargs here, if needed
    @create_tool(tool_name, description=tool.description, args_schema=tool.args_schema, infer_schema=False)
    def call_tool_with_interrupt(config: RunnableConfig, **kwargs):
        tool_input = kwargs
        request = {
            "action_request": {
                "action": tool.name,
                "args": _get_tool_input_display_kwargs(tool_input, tool.tool_call_schema)
            },
            "config": interrupt_config,
        }
        if interrupt_description:
            request["description"] = interrupt_description

        response = interrupt([request])
        if response["type"] == "accept":
            # we can call the tool as is!
            tool_response = tool.invoke(tool_input, config)
        elif response["type"] == "edit":
            tool_input = response["args"]["args"]
            # can optionally update AI message to include updated tool call
            # to avoid confusing the LLM. this would just mean returning a Command
            # with state update
            tool_response = tool.invoke(tool_input, config)
        elif response["type"] == "response":
            user_feedback = response["args"]
            tool_response = user_feedback
        elif response["type"] == "ignore":
            # can make this customizable
            tool_response = "Tool execution cancelled"

        return tool_response

    return call_tool_with_interrupt