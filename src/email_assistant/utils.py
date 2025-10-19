from typing import List, Any
import json
import html2text
from langchain.chat_models import init_chat_model
from email_assistant.prompts import PDF_SUMMARISER_PROMPT
from email_assistant.schemas import PDFSummary

def format_email_markdown(subject, author, to, email_thread, email_id=None):
    """Format email details into a nicely formatted markdown string for display
    
    Args:
        subject: Email subject
        author: Email sender
        to: Email recipient
        email_thread: Email content
        email_id: Optional email ID (for Gmail API)
    """
    id_section = f"\n**ID**: {email_id}" if email_id else ""
    
    return f"""

**Subject**: {subject}
**From**: {author}
**To**: {to}{id_section}

{email_thread}

---
"""

def format_gmail_markdown(subject, author, to, email_thread, email_id=None):
    """Format Gmail email details into a nicely formatted markdown string for display,
    with HTML to text conversion for HTML content.
    
    Args:
        subject: Email subject
        author: Email sender
        to: Email recipient
        email_thread: Email content (possibly HTML)
        email_id: Optional email ID (for Gmail API)
    """  # noqa: D205
    id_section = f"\n**ID**: {email_id}" if email_id else ""
    
    # Check if email_thread is HTML content and convert to text if needed
    if email_thread and (email_thread.strip().startswith("<!DOCTYPE") or 
                          email_thread.strip().startswith("<html") or
                          "<body" in email_thread):
        # Convert HTML to markdown text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0  # Don't wrap text
        email_thread = h.handle(email_thread)
    
    return f"""

**Subject**: {subject}
**From**: {author}
**To**: {to}{id_section}

{email_thread}

---
"""

def format_for_display(tool_call):
    """Format content for display in Agent Inbox
    
    Args:
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

Arguments:"""
        
        # Check if args is a dictionary or string
        if isinstance(tool_call["args"], dict):
            display += f"\n{json.dumps(tool_call['args'], indent=2)}\n"
        else:
            display += f"\n{tool_call['args']}\n"
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

def parse_gmail(email_input: dict) -> tuple[str, str, str, str, str, list]:
    """Parse an email input dictionary for Gmail, including the email ID and PDF attachments.

    This function extends parse_email by also returning the email ID and PDF attachments,
    which is used specifically in the Gmail integration.

    Args:
        email_input (dict): Dictionary containing email fields in any of these formats:
            Gmail schema:
                - From: Sender's email
                - To: Recipient's email
                - Subject: Email subject line
                - Body: Full email content
                - Id: Gmail message ID
                - pdf_attachments: List of PDF attachments (optional)

    Returns:
        tuple[str, str, str, str, str, list]: Tuple containing:
            - author: Sender's name and email
            - to: Recipient's name and email
            - subject: Email subject line
            - email_thread: Full email content
            - email_id: Email ID (or None if not available)
            - pdf_attachments: List of PDF attachments with filename and content (empty list if none)
    """
    print("!Email_input from Gmail!")
    print(email_input)

    # Gmail schema
    return (
        email_input["from"],
        email_input["to"],
        email_input["subject"],
        email_input["body"],
        email_input["id"],
        email_input.get("pdf_attachments", []),
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

def extract_tool_calls(messages: List[Any]) -> List[str]:
    """Extract tool call names from messages, safely handling messages without tool_calls."""
    tool_call_names = []
    for message in messages:
        # Check if message is a dict and has tool_calls
        if isinstance(message, dict) and message.get("tool_calls"):
            tool_call_names.extend([call["name"].lower() for call in message["tool_calls"]])
        # Check if message is an object with tool_calls attribute
        elif hasattr(message, "tool_calls") and message.tool_calls:
            tool_call_names.extend([call["name"].lower() for call in message.tool_calls])
    
    return tool_call_names

def format_messages_string(messages: List[Any]) -> str:
    """Format messages into a single string for analysis."""
    return '\n'.join(message.pretty_repr() for message in messages)

def show_graph(graph, xray=False):
    """Display a LangGraph mermaid diagram with fallback rendering.
    
    Handles timeout errors from mermaid.ink by falling back to pyppeteer.
    
    Args:
        graph: The LangGraph object that has a get_graph() method
    """
    from IPython.display import Image
    try:
        # Try the default renderer first
        return Image(graph.get_graph(xray=xray).draw_mermaid_png())
    except Exception as e:
        # Fall back to pyppeteer if the default renderer fails
        import nest_asyncio
        nest_asyncio.apply()
        from langchain_core.runnables.graph import MermaidDrawMethod
        return Image(graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER))
    
def summarise_pdf(text:str, filename: str, char_limit: int = 10000) -> PDFSummary:
    """Summarise PDF text using an LLM into key points, actions, deadlines.
    
    Args:
        text: The full text content of the PDF
        filename: The name of the PDF file
        char_limit: Character limit for the LLM input (default 10,000)
        
    Returns:
        PDFSummary: The summary of the PDF content
    """
    # Check to see if file is readable
    if not text:
        return PDFSummary(
            filename=filename,
            original_length=0,
            key_points=[],
            actions=[],
            deadlines=[],
            unreadable_flag=True
        )

    # Truncate text to char limit
    truncated_text = text[:char_limit]
    
    # Initialise chat model
    llm = init_chat_model("openai:gpt-4.1", temperature=0.0)
    
    # Create prompt
    prompt = PDF_SUMMARISER_PROMPT.format(filename=filename, pdf_text=truncated_text)
    
    # get raw content from LLM after prompting
    raw = llm.invoke([{"role": "user", "content": prompt}]).content
    print("raw prompt for summarisation of PDF")
    print(raw)
    
    # load in the json file that was provided by the LLM
    data = json.loads(raw)

    return PDFSummary(
        filename=filename,
        original_length=len(text),
        key_points=data.get("key_points", []),
        actions=data.get("actions", []),
        deadlines=data.get("deadlines", []),
        unreadable_flag=bool(data.get("unreadable_flag", False)),
    )