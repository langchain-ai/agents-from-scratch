from langsmith import Client
from langsmith import testing as t

import os
import matplotlib.pyplot as plt
from datetime import datetime

from eval.email_dataset import examples_triage

from email_assistant.email_assistant import email_assistant

# Client 
client = Client()

# Dataset name
dataset_name = "Interrupt Workshop: E-mail Triage Dataset"

# If the dataset doesn't exist, create it
if not client.has_dataset(dataset_name=dataset_name):

    # Create the dataset
    dataset = client.create_dataset(
        dataset_name=dataset_name, 
        description="A dataset of e-mails and their triage decisions."
    )

    # Add examples to the dataset
    client.create_examples(dataset_id=dataset.id, examples=examples_triage)

# Target functions that run our email assistants
def target_email_assistant(inputs: dict) -> dict:
    """Process an email through the workflow-based email assistant.
    
    Args:
        inputs: A dictionary containing the email_input field from the dataset
        
    Returns:
        A formatted dictionary with the assistant's response messages
    """
    try:
        response = email_assistant.invoke({"email_input": inputs["email_input"]})
        if "classification_decision" in response:
            return {"classification_decision": response['classification_decision']}
        else:
            print("No classification_decision in response from workflow agent")
            return {"classification_decision": "unknown"}
    except Exception as e:
        print(f"Error in workflow agent: {e}")
        return {"classification_decision": "unknown"}

## Evaluator 
feedback_key = "classification" # Key saved to langsmith

def classification_evaluator(outputs: dict, reference_outputs: dict) -> bool:
    """Check if the answer exactly matches the expected answer."""
    return outputs["classification_decision"].lower() == reference_outputs["classification"].lower()

experiment_results_workflow = client.evaluate(
    # Run agent 
    target_email_assistant,
    # Dataset name   
    data=dataset_name,
    # Evaluator
    evaluators=[
        classification_evaluator
    ],
    # Name of the experiment
    experiment_prefix="E-mail assistant workflow", 
    # Number of concurrent evaluations
    max_concurrency=2, 
)

## Add visualization
# Convert evaluation results to pandas dataframes
df_workflow = experiment_results_workflow.to_pandas()

# Calculate mean scores (values are on a 0-1 scale)
workflow_score = df_workflow[f'feedback.classification_evaluator'].mean() if f'feedback.classification_evaluator' in df_workflow.columns else 0.0

# Create a bar plot comparing the two models
plt.figure(figsize=(10, 6))
models = ['Agentic Workflow']
scores = [workflow_score]

# Create bars with distinct colors
plt.bar(models, scores, color=['#5DA5DA', '#FAA43A'], width=0.5)

# Add labels and title
plt.xlabel('Agent Type')
plt.ylabel('Average Score')
plt.title(f'Email Triage Performance Comparison - {feedback_key.capitalize()} Score')

# Add score values on top of bars
for i, score in enumerate(scores):
    plt.text(i, score + 0.02, f'{score:.2f}', ha='center', fontweight='bold')

# Set y-axis limit
plt.ylim(0, 1.1)

# Add grid lines for better readability
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Ensure the output directory exists
os.makedirs('eval/results', exist_ok=True)

# Save the plot with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
plot_path = f'eval/results/triage_comparison_{timestamp}.png'
plt.savefig(plot_path)
plt.close()

print(f"\nEvaluation visualization saved to: {plot_path}")
print(f"Agent With Router Score: {workflow_score:.2f}")

