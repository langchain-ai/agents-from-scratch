from typing import Literal
from pydantic import BaseModel

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.prebuilt.interrupt import HumanInterruptConfig

from email_assistant.prompts import triage_system_prompt, triage_user_prompt, agent_system_prompt_hitl, default_background, default_triage_instructions, default_response_preferences, default_cal_preferences
from email_assistant.schemas import State, RouterSchema, StateInput
from email_assistant.utils import parse_email, format_for_display, format_email_markdown, tool_with_human_in_the_loop

# Define base agent tools
@tool
def write_email(to: str, subject: str, content: str) -> str:
    """Write and send an email."""
    # Placeholder response - in real app would send email
    return f"Email sent to {to} with subject '{subject}' and content: {content}"

@tool
def schedule_meeting(
    attendees: list[str], subject: str, duration_minutes: int, preferred_day: str
) -> str:
    """Schedule a calendar meeting."""
    # Placeholder response - in real app would check calendar and schedule
    return f"Meeting '{subject}' scheduled for {preferred_day} with {len(attendees)} attendees"

@tool
def check_calendar_availability(day: str) -> str:
    """Check calendar availability for a given day."""
    # Placeholder response - in real app would check actual calendar
    return f"Available times on {day}: 9:00 AM, 2:00 PM, 4:00 PM"

@tool
class Question(BaseModel):
      """Question to ask user."""
      content: str

# Define interrupt configs for each tool
write_email_interrupt_config = {
    "allow_ignore": True,
    "allow_respond": True,
    "allow_edit": True,
    "allow_accept": True,
}

schedule_meeting_interrupt_config = {
    "allow_ignore": True,
    "allow_respond": True,
    "allow_edit": True,
    "allow_accept": True,
}

question_interrupt_config = {
    "allow_ignore": True,
    "allow_respond": True,
    "allow_edit": False,
    "allow_accept": False,
}

# Wrap tools with human-in-the-loop functionality
write_email_hitl = tool_with_human_in_the_loop(
    write_email,
    interrupt_config=write_email_interrupt_config
)

schedule_meeting_hitl = tool_with_human_in_the_loop(
    schedule_meeting,
    interrupt_config=schedule_meeting_interrupt_config
)

question_hitl = tool_with_human_in_the_loop(
    Question,
    interrupt_config=question_interrupt_config
)
    
# All tools available to the agent
tools = [
    write_email_hitl, 
    schedule_meeting_hitl, 
    check_calendar_availability, 
    question_hitl, 
]

tools_by_name = {tool.name: tool for tool in tools}

# Initialize the LLM
llm = init_chat_model("openai:gpt-4o")

# Router LLM 
llm_router = llm.with_structured_output(RouterSchema) 
llm_with_tools = llm.bind_tools(tools)

# Nodes 
def triage_router(state: State) -> Command[Literal["triage_interrupt_handler", "response_agent", "__end__"]]:
    """Analyze email content to decide if we should respond, notify, or ignore.

    The triage step prevents the assistant from wasting time on:
    - Marketing emails and spam
    - Company-wide announcements
    - Messages meant for other teams
    """
        
    # Format system prompt with background and triage instructions
    system_prompt = triage_system_prompt.format(
        background=default_background,
        triage_instructions=default_triage_instructions
    )

    # Parse the email input
    author, to, subject, email_thread = parse_email(state["email_input"])
    user_prompt = triage_user_prompt.format(
        author=author, to=to, subject=subject, email_thread=email_thread
    )

    # Create email markdown for Agent Inbox in case of notification  
    email_markdown = format_email_markdown(subject, author, to, email_thread)

    # Run the router LLM
    result = llm_router.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    # Decision
    classification = result.classification
    messages = [{"role": "user",
                "content": f"Classification Decision: {classification}"
                }]

    # Process the classification decision
    if classification == "respond":
        print("📧 Classification: RESPOND - This email requires a response")
        # Next node
        goto = "response_agent"
        # Add the email to the messages
        messages.append({"role": "user",
                            "content": f"Respond to the email: {email_markdown}"
                            })
        # Update the state
        update = {
            "messages": messages,
            "classification_decision": classification,
        }
    elif classification == "ignore":
        print("🚫 Classification: IGNORE - This email can be safely ignored")

        # Next node
        goto = END
        # Update the state
        update = {
            "messages": messages,
            "classification_decision": classification,
        }

    elif classification == "notify":
        print("🔔 Classification: NOTIFY - This email contains important information") 

        # Next node
        goto = "triage_interrupt_handler"
        # Update the state
        update = {
            "messages": messages,
            "classification_decision": classification,
        }

    else:
        raise ValueError(f"Invalid classification: {classification}")
    return Command(goto=goto, update=update)

def triage_interrupt_handler(state: State) -> Command[Literal["response_agent", "__end__"]]:
    """Handles interrupts from the triage step"""
    
    # Parse the email input
    author, to, subject, email_thread = parse_email(state["email_input"])

    # Create email markdown for Agent Inbox in case of notification  
    email_markdown = format_email_markdown(subject, author, to, email_thread)

    # Create messages to save to memory
    messages = [{"role": "user",
                "content": f"Classification Decision: {state['classification_decision']} for email: {email_markdown}"
                }]
    
    # Define interrupt config for triage
    triage_interrupt_config = {
        "allow_ignore": True,  
        "allow_respond": True, 
        "allow_edit": False, 
        "allow_accept": False,  
    }

    # Create interrupt for Agent Inbox using the same pattern as tool interrupts
    request = {
        "action_request": {
            "action": f"Email Assistant: {state['classification_decision']}",
            "args": {}
        },
        "config": triage_interrupt_config,
        "description": email_markdown,
    }

    # Send to Agent Inbox and wait for response
    response = interrupt([request])[0]

    # Accept the decision and end   
    if response["type"] == "accept":
        goto = END 

    # If user provides feedback, update memory  
    elif response["type"] == "response":
        # Add feedback to messages 
        user_input = response["args"]
        messages.append({"role": "user",
                        "content": f"Here is feedback on how the user would prefer the email to be classified: {user_input}"
                        })

        goto = END

    # Update the state 
    update = {
        "messages": messages,
    }

    return Command(goto=goto, update=update)

def llm_call(state: State):
    """LLM decides whether to call a tool or not"""

    return {
        "messages": [
            llm_with_tools.invoke(
                [
                    {"role": "system", "content": agent_system_prompt_hitl.format(background=default_background,
                                                                                  response_preferences=default_response_preferences, 
                                                                                  cal_preferences=default_cal_preferences)}
                ]
                + state["messages"]
            )
        ]
    }

def interrupt_handler(state: State):
    """Process tool calls with human-in-the-loop interrupts handled by the wrapped tools"""
    
    # Store messages
    result = []

    # Iterate over the tool calls in the last message
    for tool_call in state["messages"][-1].tool_calls:
        # Get the tool by name
        tool = tools_by_name[tool_call["name"]]
        
        # Get original email from email_input in state - for description enhancement
        original_email_markdown = ""
        if "email_input" in state:
            email_input = state["email_input"]
            author, to, subject, email_thread = parse_email(email_input)
            original_email_markdown = format_email_markdown(subject, author, to, email_thread)
        
        # Format tool call for display and prepend the original email
        # This will be added as context to tools that need interrupt_description
        tool_display = format_for_display(state, tool_call)
        description = original_email_markdown + tool_display
        
        # Execute the tool with the description as context
        # All interrupt handling is now handled by the wrapped tool itself
        observation = tool.invoke(tool_call["args"], config={"interrupt_description": description})
        result.append({"role": "tool", "content": observation, "tool_call_id": tool_call["id"]})
            
    return {"messages": result}

# Conditional edge functions
def should_continue(state: State) -> Literal["interrupt_handler", END]:
    """Route to interrupt handler if tool call made"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "interrupt_handler"
    return END

# Build workflow
agent_builder = StateGraph(State)

# Add nodes
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("interrupt_handler", interrupt_handler)

# Add edges
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    {
        "interrupt_handler": "interrupt_handler",
        END: END,
    },
)
agent_builder.add_edge("interrupt_handler", "llm_call")

# Compile the agent
response_agent = agent_builder.compile()

# Build overall workflow
overall_workflow = (
    StateGraph(State, input=StateInput)
    .add_node(triage_router)
    .add_node(triage_interrupt_handler)
    .add_node("response_agent", response_agent)
    .add_edge(START, "triage_router")
    
)

email_assistant = overall_workflow.compile()