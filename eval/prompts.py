# Used in /eval/evaluate_triage.py
TRIAGE_CLASSIFICATION_PROMPT = """

<Task>
You are evaluating the classification of emails.

They should be be classified into one of the following categories:
- ignore
- notify
- respond

You will be given:
- the email_input
- the agent's reasoning and decision as a list of messages 
- the correct classification

Your job is to evaluate the agent's reasoning and decision relative to the correct classification.
</Task>

<email_input>
{inputs}
</email_input>

<agent_response>
{outputs}
</agent_response>

<correct_classification>
{reference_outputs}
</correct_classification>
"""

# Used in /tests/test_email_assistant.py
RESPONSE_CRITERIA_SYSTEM_PROMPT = """You are evaluating an email assistant that works on behalf of a user, David Xu.

You will see a sequence of messages, starting with an email sent to David Xu <david.interrupt.demo@gmail.com>. 

You will then see the assistant's response to this email on behalf of David Xu, which includes any tool calls made (e.g., write_email, schedule_meeting, check_calendar_availability, done).

You will also see a list of criteria that the assistant's response must meet.

Your job is to evaluate if the assistant's response meets ALL the criteria bullet points provided.

IMPORTANT EVALUATION INSTRUCTIONS:
1. The assistant's response is formatted as a list of messages.
2. The response criteria are formatted as bullet points (•)
3. You must evaluate the response against EACH bullet point individually
4. ALL bullet points must be met for the response to receive a 'True' grade
5. For each bullet point, cite specific text from the response that satisfies or fails to satisfy it
6. Be objective and rigorous in your evaluation
7. In your justification, clearly indicate which criteria were met and which were not
7. If ANY criteria are not met, the overall grade must be 'False'

Your output will be used for automated testing, so maintain a consistent evaluation approach."""

# Used in /tests/test_hitl.py
HITL_FEEDBACK_SYSTEM_PROMPT = """You are evaluating an email assistant's response to determine if it meets specific criteria.

This is an email assistant that is used to respond to emails. Review our initial email response and the user feedback given to update the email response. Here is the feedback: {feedback}. Assess whether the final email response addresses the feedback that we gave."""

# Used in /tests/test_memory.py
MEMORY_UPDATE_SYSTEM_PROMPT = """This is an email assistant that uses memory to update its response preferences. 

Review the initial response preferences and the updated response preferences. Assess whether the updated response preferences are more accurate than the initial response preferences."""