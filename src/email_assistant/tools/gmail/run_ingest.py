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
import os
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langgraph_sdk import get_client
from dotenv import load_dotenv
from email_assistant.tools.gmail.gmail_tools import iter_parts, extract_pdf_text

load_dotenv()

# Setup paths
_ROOT = Path(__file__).parent.absolute()
_SECRETS_DIR = _ROOT / ".secrets"
TOKEN_PATH = _SECRETS_DIR / "token.json"
# Configurable limits (top of file or near extract_email_data)
MAX_PDF_CHARS = 25000        # truncate very long extracted text

def extract_message_part(payload):
    """Extract content from a message part."""
    # If this is multipart, process with preference for text/plain
    if payload.get("parts"):
        # First try to find text/plain part
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain" and part.get("body", {}).get("data"):
                data = part["body"]["data"]
                return base64.urlsafe_b64decode(data).decode("utf-8")
                
        # If no text/plain found, try text/html
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/html" and part.get("body", {}).get("data"):
                data = part["body"]["data"]
                return base64.urlsafe_b64decode(data).decode("utf-8")
                
        # If we still haven't found content, recursively check for nested parts
        for part in payload["parts"]:
            content = extract_message_part(part)
            if content:
                return content
    
    # Not multipart, try to get content directly
    if payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8")

    return ""

def load_gmail_credentials():
    """
    Load Gmail credentials from token.json or environment variables.
    
    This function attempts to load credentials from multiple sources in this order:
    1. Environment variables GMAIL_TOKEN
    2. Local file at token_path (.secrets/token.json)
    
    Returns:
        Google OAuth2 Credentials object or None if credentials can't be loaded
    """
    token_data = None
    
    # 1. Try environment variable
    env_token = os.getenv("GMAIL_TOKEN")
    if env_token:
        try:
            token_data = json.loads(env_token)
            print("Using GMAIL_TOKEN environment variable")
        except Exception as e:
            print(f"Could not parse GMAIL_TOKEN environment variable: {str(e)}")
    
    # 2. Try local file as fallback
    if token_data is None:
        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH, "r") as f:
                    token_data = json.load(f)
                print(f"Using token from {TOKEN_PATH}")
            except Exception as e:
                print(f"Could not load token from {TOKEN_PATH}: {str(e)}")
        else:
            print(f"Token file not found at {TOKEN_PATH}")
    
    # If we couldn't get token data from any source, return None
    if token_data is None:
        print("Could not find valid token data in any location")
        return None
    
    try:
        # Create credentials object
        credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"])
        )
        return credentials
    except Exception as e:
        print(f"Error creating credentials object: {str(e)}")
        return None

def extract_email_data(message, service=None):
    """Extract key information from a Gmail message."""
    headers = message['payload']['headers']
    
    # Extract key headers
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
    to_email = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
    
    # Extract message content
    content = extract_message_part(message['payload'])
    # Additionally, extract text from any PDF attachments
    pdf_attachments = []
    if service:
        for part in iter_parts(message['payload']):
            if part.get('mimeType') == "application/pdf":
                text = extract_pdf_text(service, message['id'], part)
                if len(text) > MAX_PDF_CHARS:
                    text = text[:MAX_PDF_CHARS] + "\n...[truncated]..."
                filename = part.get('filename')
                for h in part.get("headers", []):
                    if h.get("name","").lower() in {"content-disposition","content-type"} and "filename=" in h.get("value",""):
                            filename = h["value"].split("filename=")[-1].strip().strip('"')
                pdf_attachments.append({"filename": filename, "content": text})
    
    # Create email data object
    email_data = {
        "from_email": from_email,
        "to_email": to_email,
        "subject": subject,
        "page_content": content,
        "pdf_attachments": pdf_attachments, #NEW
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
    
    thread_exists = False
    try:
        # Try to get existing thread info
        thread_info = await client.threads.get(thread_id)
        thread_exists = True
        print(f"Found existing thread: {thread_id}")
    except Exception as e:
        # If thread doesn't exist, create it
        print(f"Creating new thread: {thread_id}")
        thread_info = await client.threads.create(thread_id=thread_id)
    
    # If thread exists, clean up previous runs
    if thread_exists:
        try:
            # List all runs for this thread
            runs = await client.runs.list(thread_id)

            # Delete all previous runs to avoid state accumulation
            for run_info in runs:
                # Handle both dict and object responses from SDK
                run_id = run_info.get('run_id') if isinstance(run_info, dict) else run_info.run_id
                print(f"Deleting previous run {run_id} from thread {thread_id}")
                try:
                    await client.runs.delete(thread_id, run_id)
                except Exception as e:
                    print(f"Failed to delete run {run_id}: {str(e)}")
        except Exception as e:
            print(f"Error listing/deleting runs: {str(e)}")
    
    # Update thread metadata with current email ID
    await client.threads.update(thread_id, metadata={"email_id": email_data["id"]})
    
    # Create a fresh run for this email
    print(f"Creating run for thread {thread_id} with graph {graph_name}")
    
    run = await client.runs.create(
        thread_id,
        graph_name,
        input={"email_input": {
            "from": email_data["from_email"],
            "to": email_data["to_email"],
            "subject": email_data["subject"],
            "body": email_data["page_content"],
            "pdf_attachments": email_data["pdf_attachments"], #NEW
            "id": email_data["id"]
        }},
        multitask_strategy="rollback",
    )
    
    print(f"Run created successfully with thread ID: {thread_id}")
    
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
            email_data = extract_email_data(message, service=service)
            
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
        default="email_assistant_hitl_memory_gmail",
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