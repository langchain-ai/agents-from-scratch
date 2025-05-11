#!/usr/bin/env python
"""
Simple Gmail ingestion script based directly on test.ipynb that works with LangSmith tracing.

This script provides a minimal implementation for ingesting emails to the LangGraph server,
with reliable LangSmith tracing.
"""

import base64
import json
import uuid
import hashlib
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langgraph_sdk import get_client
import os
from dotenv import load_dotenv

# Setup nest_asyncio for asyncio support
try:
    import nest_asyncio
    nest_asyncio.apply()
    print("Applied nest_asyncio patch")
except ImportError:
    print("Warning: nest_asyncio not available. Install with: pip install nest_asyncio")

# Setup paths
_ROOT = Path(__file__).parent.absolute()
_SECRETS_DIR = _ROOT / ".secrets"
TOKEN_PATH = _SECRETS_DIR / "token.json"

# Load environment variables
load_dotenv()

def extract_message_part(payload):
    """Extract content from a message part."""
    if payload.get("body", {}).get("data"):
        # Handle base64 encoded content
        data = payload["body"]["data"]
        decoded = base64.urlsafe_b64decode(data).decode("utf-8")
        return decoded

    # Handle multipart messages
    if payload.get("parts"):
        text_parts = []
        for part in payload["parts"]:
            # Recursively process parts
            content = extract_message_part(part)
            if content:
                text_parts.append(content)
        return "\n".join(text_parts)

    return ""

def load_gmail_credentials():
    """Load Gmail credentials from environment variables"""
    try:
        credentials = Credentials(
            token=os.getenv("GOOGLE_ACCESS_TOKEN"),
            refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/calendar"]
        )
        return credentials
    except Exception as e:
        print(f"Error loading credentials from environment variables: {str(e)}")
        return None

def extract_email_data(message):
    """Extract key information from a Gmail message."""
    headers = message['payload']['headers']
    
    # Extract key headers
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
    to_email = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
    
    # Extract message content
    content = extract_message_part(message['payload'])
    
    # Create email data object
    email_data = {
        "from_email": from_email,
        "to_email": to_email,
        "subject": subject,
        "page_content": content,
        "id": message['id'],
        "thread_id": message['threadId'],
        "send_time": date
    }
    
    return email_data

async def ingest_email_to_langgraph(email_data, graph_name, url="http://127.0.0.1:2024"):
    """Ingest an email to LangGraph."""
    # Connect to LangGraph server
    client = get_client(url=url)
    
    # Create a consistent UUID for the thread
    raw_thread_id = email_data["thread_id"]
    thread_id = str(
        uuid.UUID(hex=hashlib.md5(raw_thread_id.encode("UTF-8")).hexdigest())
    )
    print(f"Gmail thread ID: {raw_thread_id} → LangGraph thread ID: {thread_id}")
    
    try:
        # Try to get existing thread info
        thread_info = await client.threads.get(thread_id)
        print(f"Found existing thread: {thread_id}")
    except Exception as e:
        # If thread doesn't exist, create it
        print(f"Creating new thread: {thread_id}")
        thread_info = await client.threads.create(thread_id=thread_id)
    
    # Update thread metadata with current email ID
    await client.threads.update(thread_id, metadata={"email_id": email_data["id"]})
    
    # Create a run for this email
    print(f"Creating run for thread {thread_id} with graph {graph_name}")
    
    run = await client.runs.create(
        thread_id,
        graph_name,
        input={"email_input": {
            "from": email_data["from_email"],
            "to": email_data["to_email"],
            "subject": email_data["subject"],
            "body": email_data["page_content"],
            "id": email_data["id"]
        }},
        multitask_strategy="rollback",
    )
    
    print(f"Run created successfully")
    print(f"View in LangGraph Studio: http://127.0.0.1:2024/threads/{thread_id}")
    
    return thread_id, run

async def fetch_and_process_emails(args):
    """Fetch emails from Gmail and process them through LangGraph."""
    # Load Gmail credentials
    credentials = load_gmail_credentials()
    if not credentials:
        print("Failed to load Gmail credentials")
        return 1
        
    # Build Gmail service
    service = build("gmail", "v1", credentials=credentials)
    
    # Process emails
    processed_count = 0
    
    try:
        # Get messages from the specified email address
        email_address = args.email
        
        # Construct Gmail search query
        query = f"to:{email_address} OR from:{email_address}"
        
        # Add time constraint if specified
        if args.minutes_since > 0:
            # Calculate timestamp for filtering
            from datetime import timedelta
            after = int((datetime.now() - timedelta(minutes=args.minutes_since)).timestamp())
            query += f" after:{after}"
            
        # Only include unread emails unless include_read is True
        if not args.include_read:
            query += " is:unread"
            
        print(f"Gmail search query: {query}")
        
        # Execute the search
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        
        if not messages:
            print("No emails found matching the criteria")
            return 0
            
        print(f"Found {len(messages)} emails")
        
        # Process each email
        for i, message_info in enumerate(messages):
            # Stop early if requested
            if args.early and i > 0:
                print(f"Early stop after processing {i} emails")
                break
                
            # Check if we should reprocess this email
            if not args.rerun:
                # TODO: Add check for already processed emails
                pass
                
            # Get the full message
            message = service.users().messages().get(userId="me", id=message_info["id"]).execute()
            
            # Extract email data
            email_data = extract_email_data(message)
            
            print(f"\nProcessing email {i+1}/{len(messages)}:")
            print(f"From: {email_data['from_email']}")
            print(f"Subject: {email_data['subject']}")
            
            # Ingest to LangGraph
            thread_id, run = await ingest_email_to_langgraph(
                email_data, 
                args.graph_name,
                url=args.url
            )
            
            processed_count += 1
            
        print(f"\nProcessed {processed_count} emails successfully")
        return 0
        
    except Exception as e:
        print(f"Error processing emails: {str(e)}")
        return 1

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Simple Gmail ingestion for LangGraph with reliable tracing")
    
    parser.add_argument(
        "--email", 
        type=str, 
        required=True,
        help="Email address to fetch messages for"
    )
    parser.add_argument(
        "--minutes-since", 
        type=int, 
        default=120,
        help="Only retrieve emails newer than this many minutes"
    )
    parser.add_argument(
        "--graph-name", 
        type=str, 
        default="email_assistant_hitl_memory",
        help="Name of the LangGraph to use"
    )
    parser.add_argument(
        "--url", 
        type=str, 
        default="http://127.0.0.1:2024",
        help="URL of the LangGraph deployment"
    )
    parser.add_argument(
        "--early", 
        action="store_true",
        help="Early stop after processing one email"
    )
    parser.add_argument(
        "--include-read",
        action="store_true",
        help="Include emails that have already been read"
    )
    parser.add_argument(
        "--rerun", 
        action="store_true",
        help="Process the same emails again even if already processed"
    )
    parser.add_argument(
        "--skip-filters",
        action="store_true",
        help="Skip filtering of emails"
    )
    return parser.parse_args()

if __name__ == "__main__":
    # Get command line arguments
    args = parse_args()
    
    # Run the script
    exit(asyncio.run(fetch_and_process_emails(args)))