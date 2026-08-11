
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
import pytest
from src.email_assistant.eval.email_dataset import email_inputs, expected_tool_calls
from src.email_assistant.utils import format_messages_string
from src.email_assistant.email_assistant import email_assistant
from src.email_assistant.utils import extract_tool_calls
from langsmith import testing as t
from dotenv import load_dotenv

load_dotenv(".env")

@pytest.mark.langsmith
@pytest.mark.parametrize(
    "email_input, expected_calls",
    [   # Pick some examples with e-mail reply expected
        (email_inputs[0],expected_tool_calls[0]),
        (email_inputs[3],expected_tool_calls[3]),
    ],
)
def test_email_dataset_tool_calls(email_input, expected_calls):
    """Test if email processing contains expected tool calls."""    
    # Run the email assistant
    result = email_assistant.invoke({"email_input": email_input})
            
    # Extract tool calls from messages list
    extracted_tool_calls = extract_tool_calls(result['messages'])
            
    # Check if all expected tool calls are in the extracted ones
    missing_calls = [call for call in expected_calls if call.lower() not in extracted_tool_calls]
    
    t.log_outputs({
                "missing_calls": missing_calls,
                "extracted_tool_calls": extracted_tool_calls,
                "response": format_messages_string(result['messages'])
            })

    # Test passes if no expected calls are missing
    assert len(missing_calls) == 0
