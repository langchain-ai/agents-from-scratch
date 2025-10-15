"""
Gmail tools implementation module. 
This module formats the Gmail API functions into LangChain tools.
"""

import os
import sys
import base64
import email.utils
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Iterator
from pathlib import Path
from pydantic import Field, BaseModel
from langchain_core.tools import tool

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define paths for credentials and tokens
_ROOT = Path(__file__).parent.absolute()
_SECRETS_DIR = _ROOT / ".secrets"

# We need to try importing the Gmail API libraries
# If they're not available, we'll use a mock implementation
try:
    import logging
    from googleapiclient.discovery import build
    from email.mime.text import MIMEText
    from datetime import timedelta
    from dateutil.parser import parse as parse_time
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    import pdfplumber
    import io 
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Email content extraction function
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
    def iter_parts(payload):
        """Yield every MIME part in a Gmail message (depth‑first).

        The Gmail message/part `payload` may contain nested `parts` lists (multipart/*).
        This flattens that hierarchy so callers can scan all parts (e.g. to
        locate attachments like application/pdf or choose a text/plain body).

        Args:
            payload (dict|None): Root message or part dict (may have 'parts').

        Yields:
            dict: Each part including the root, then all descendants.
        """
        if not payload:
            return
        yield payload
        for child in payload.get("parts") or []:
            yield from iter_parts(child)

    def extract_pdf_text(service, message_id, part):
        """Download + extract text from a PDF attachment using pdfplumber."""
        if pdfplumber is None:
            return ""
        att_id = part.get("body", {}).get("attachmentId")
        if not att_id:
            return ""
        att = (service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=message_id, id=att_id)
                    .execute())
        data = att.get("data")
        if not data:
            return ""
        pdf_bytes = base64.urlsafe_b64decode(data)
        try:
            text_pages = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    try:
                        text_pages.append(page.extract_text() or "")
                    except Exception:
                        text_pages.append("")
            return "\n\n".join(t for t in text_pages if t).strip()
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            return ""
    
    # Function to get credentials from token.json or environment variables
    def get_credentials(gmail_token=None, gmail_secret=None):
        """
        Get Gmail API credentials from token.json or environment variables.
        
        This function attempts to load credentials from multiple sources in this order:
        1. Directly passed gmail_token and gmail_secret parameters
        2. Environment variables GMAIL_TOKEN and GMAIL_SECRET
        3. Local files at token_path (.secrets/token.json) and secrets_path (.secrets/secrets.json)
        
        Args:
            gmail_token: Optional JSON string containing token data
            gmail_secret: Optional JSON string containing credentials
            
        Returns:
            Google OAuth2 Credentials object or None if credentials can't be loaded
        """
        token_path = _SECRETS_DIR / "token.json"
        token_data = None
        
        # Try to get token data from various sources
        if gmail_token:
            # 1. Use directly passed token parameter if available
            try:
                token_data = json.loads(gmail_token) if isinstance(gmail_token, str) else gmail_token
                logger.info("Using directly provided gmail_token parameter")
            except Exception as e:
                logger.warning(f"Could not parse provided gmail_token: {str(e)}")
                
        if token_data is None:
            # 2. Try environment variable
            env_token = os.getenv("GMAIL_TOKEN")
            if env_token:
                try:
                    token_data = json.loads(env_token)
                    logger.info("Using GMAIL_TOKEN environment variable")
                except Exception as e:
                    logger.warning(f"Could not parse GMAIL_TOKEN environment variable: {str(e)}")
        
        if token_data is None:
            # 3. Try local file
            if os.path.exists(token_path):
                try:
                    with open(token_path, "r") as f:
                        token_data = json.load(f)
                    logger.info(f"Using token from {token_path}")
                except Exception as e:
                    logger.warning(f"Could not load token from {token_path}: {str(e)}")
        
        # If we couldn't get token data from any source, return None
        if token_data is None:
            logger.error("Could not find valid token data in any location")
            return None
        
        try:
            from google.oauth2.credentials import Credentials
            
            # Create credentials object with specific format
            credentials = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"])
            )
            
            # Add authorize method to make it compatible with old code
            credentials.authorize = lambda request: request
            
            return credentials
        except Exception as e:
            logger.error(f"Error creating credentials object: {str(e)}")
            return None
    
    # Type alias for better readability
    EmailData = Dict[str, Any]
    
    GMAIL_API_AVAILABLE = True
    
except ImportError:
    # If Gmail API libraries aren't available, set flag to use mock implementation
    GMAIL_API_AVAILABLE = False
    pdfplumber = None
    logger = logging.getLogger(__name__)

# Helper function that is used by the tool and can be imported elsewhere
def fetch_group_emails(
    email_address: str,
    minutes_since: int = 30,
    gmail_token: Optional[str] = None,
    gmail_secret: Optional[str] = None,
    include_read: bool = False,
    skip_filters: bool = False,
) -> Iterator[Dict[str, Any]]:
    """
    Fetch recent emails from Gmail that involve the specified email address.
    
    This function retrieves emails where the specified address is either a sender
    or recipient, processes them, and returns them in a format suitable for the
    email assistant to process.
    
    Args:
        email_address: Email address to fetch messages for
        minutes_since: Only retrieve emails newer than this many minutes
        gmail_token: Optional token for Gmail API authentication
        gmail_secret: Optional credentials for Gmail API authentication
        include_read: Whether to include already read emails (default: False)
        skip_filters: Skip thread and sender filtering (return all messages, default: False)
        
    Yields:
        Dict objects containing processed email information
    """
    use_mock = False
    
    # Check if we need to use mock implementation
    if not GMAIL_API_AVAILABLE:
        logger.info("Gmail API not available, using mock implementation")
        use_mock = True
    
    # Check if required credential files exist
    if not use_mock and not gmail_token and not gmail_secret:
        token_path = str(_SECRETS_DIR / "token.json")
        secrets_path = str(_SECRETS_DIR / "secrets.json")
        
        if not os.path.exists(token_path) and not os.path.exists(secrets_path):
            logger.warning(f"No Gmail API credentials found. Looking for token.json or secrets.json in .secrets directory")
            logger.warning("Using mock implementation instead")
            use_mock = True
    
    # Return mock data if needed
    if use_mock:
        # For demo purposes, we return a mock email
        mock_email = {
            "from_email": "sender@example.com",
            "to_email": email_address,
            "subject": "Sample Email Subject",
            "page_content": "This is a sample email body for testing the email assistant.",
            "id": "mock-email-id-123",
            "thread_id": "mock-thread-id-123",
            "send_time": datetime.now().isoformat()
        }
        
        yield mock_email
        return
    
    try:
        # Get Gmail API credentials from parameters, environment variables, or local files
        creds = get_credentials(gmail_token, gmail_secret)
        
        # Check if credentials are valid
        if not creds or not hasattr(creds, 'authorize'):
            logger.warning("Invalid Gmail credentials, using mock implementation")
            logger.warning("Ensure GMAIL_TOKEN environment variable is set or token.json file exists")
            mock_email = {
                "from_email": "sender@example.com",
                "to_email": email_address,
                "subject": "Sample Email Subject - Invalid Credentials",
                "page_content": "This is a mock email because the Gmail credentials are invalid.",
                "id": "mock-email-id-123",
                "thread_id": "mock-thread-id-123",
                "send_time": datetime.now().isoformat()
            }
            yield mock_email
            return
            
        service = build("gmail", "v1", credentials=creds)
        
        # Calculate timestamp for filtering
        after = int((datetime.now() - timedelta(minutes=minutes_since)).timestamp())
        
        # Construct Gmail search query
        # This query searches for:
        # - Emails sent to or from the specified address
        # - Emails after the specified timestamp
        # - Including emails from all categories (inbox, updates, promotions, etc.)
        
        # Base query with time filter
        query = f"(to:{email_address} OR from:{email_address}) after:{after}"
        
        # Only include unread emails unless include_read is True
        if not include_read:
            query += " is:unread"
        else:
            logger.info("Including read emails in search")
            
        # Log the final query for debugging
        logger.info(f"Gmail search query: {query}")
            
        # Additional filter options (commented out by default)
        # If you want to include emails from specific categories, use:
        # query += " category:(primary OR updates OR promotions)"
        
        # Retrieve all matching messages (handling pagination)
        messages = []
        nextPageToken = None
        logger.info(f"Fetching emails for {email_address} from last {minutes_since} minutes")
        
        while True:
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, pageToken=nextPageToken)
                .execute()
            )
            if "messages" in results:
                new_messages = results["messages"]
                messages.extend(new_messages)
                logger.info(f"Found {len(new_messages)} messages in this page")
            else:
                logger.info("No messages found in this page")
                
            nextPageToken = results.get("nextPageToken")
            if not nextPageToken:
                logger.info(f"Total messages found: {len(messages)}")
                break

        # Process each message
        count = 0
        for message in messages:
            try:
                # Get full message details
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                thread_id = msg["threadId"]
                payload = msg["payload"]
                headers = payload.get("headers", [])
                
                # Get thread details to determine conversation context
                # Directly fetch the complete thread without any format restriction
                # This matches the exact approach in the test code that successfully gets all messages
                thread = service.users().threads().get(userId="me", id=thread_id).execute()
                messages_in_thread = thread["messages"]
                logger.info(f"Retrieved thread {thread_id} with {len(messages_in_thread)} messages")
                
                # Sort messages by internalDate to ensure proper chronological ordering
                # This ensures we correctly identify the latest message
                if all("internalDate" in msg for msg in messages_in_thread):
                    messages_in_thread.sort(key=lambda m: int(m.get("internalDate", 0)))
                    logger.info(f"Sorted {len(messages_in_thread)} messages by internalDate")
                else:
                    # Fallback to ID-based sorting if internalDate is missing
                    messages_in_thread.sort(key=lambda m: m["id"])
                    logger.info(f"Sorted {len(messages_in_thread)} messages by ID (internalDate missing)")
                
                # Log details about the messages in the thread for debugging
                for idx, msg in enumerate(messages_in_thread):
                    headers = msg["payload"]["headers"]
                    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                    from_email = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                    date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")
                    logger.info(f"  Message {idx+1}/{len(messages_in_thread)}: ID={msg['id']}, Date={date}, From={from_email}")
                
                # Log thread information for debugging
                logger.info(f"Thread {thread_id} has {len(messages_in_thread)} messages")
                
                # Analyze the last message in the thread to determine if we need to process it
                last_message = messages_in_thread[-1]
                last_headers = last_message["payload"]["headers"]
                
                # Get sender of last message
                from_header = next(
                    header["value"] for header in last_headers if header["name"] == "From"
                )
                last_from_header = next(
                    header["value"]
                    for header in last_message["payload"].get("headers")
                    if header["name"] == "From"
                )
                
                # If the last message was sent by the user, mark this as a user response
                # and don't process it further (assistant doesn't need to respond to user's own emails)
                if email_address in last_from_header:
                    yield {
                        "id": message["id"],
                        "thread_id": message["threadId"],
                        "user_respond": True,
                    }
                    continue
                    
                # Check if this is a message we should process
                is_from_user = email_address in from_header
                is_latest_in_thread = message["id"] == last_message["id"]
                
                # Modified logic for skip_filters:
                # 1. When skip_filters is True, process all messages regardless of position in thread
                # 2. When skip_filters is False, only process if it's not from user AND is latest in thread
                should_process = skip_filters or (not is_from_user and is_latest_in_thread)
                
                if not should_process:
                    if is_from_user:
                        logger.debug(f"Skipping message {message['id']}: sent by the user")
                    elif not is_latest_in_thread:
                        logger.debug(f"Skipping message {message['id']}: not the latest in thread")
                
                # Process the message if it passes our filters (or if filters are skipped)
                if should_process:
                    # Log detailed information about this message
                    logger.info(f"Processing message {message['id']} from thread {thread_id}")
                    logger.info(f"  Is latest in thread: {is_latest_in_thread}")
                    logger.info(f"  Skip filters enabled: {skip_filters}")
                    
                    # If the user wants to process the latest message in the thread,
                    # use the last_message from the thread API call instead of the original message
                    # that matched the search query
                    if not skip_filters:
                        # Use original message if skip_filters is False
                        process_message = message
                        process_payload = payload
                        process_headers = headers
                    else:
                        # Use the latest message in the thread if skip_filters is True
                        process_message = last_message
                        process_payload = last_message["payload"]
                        process_headers = process_payload.get("headers", [])
                        logger.info(f"Using latest message in thread: {process_message['id']}")
                    
                    # Extract email metadata from headers
                    subject = next(
                        header["value"] for header in process_headers if header["name"] == "Subject"
                    )
                    from_email = next(
                        (header["value"] for header in process_headers if header["name"] == "From"),
                        "",
                    ).strip()
                    _to_email = next(
                        (header["value"] for header in process_headers if header["name"] == "To"),
                        "",
                    ).strip()
                    
                    # Use Reply-To header if present
                    if reply_to := next(
                        (
                            header["value"]
                            for header in process_headers
                            if header["name"] == "Reply-To"
                        ),
                        "",
                    ).strip():
                        from_email = reply_to
                        
                    # Extract and parse email timestamp
                    send_time = next(
                        header["value"] for header in process_headers if header["name"] == "Date"
                    )
                    parsed_time = parse_time(send_time)
                    
                    # Extract email body content
                    body = extract_message_part(process_payload)

                    pdf_attachments = []
                    for part in iter_parts(process_payload):
                        if part.get("mimeType") == "application/pdf":
                            content = extract_pdf_text(service, process_message["id"], part)
                            if content:
                                filename = part.get("filename") or "attachment.pdf"
                                for h in part.get("headers", []) or []:
                                    if h.get("name", "").lower() in {"content-disposition", "content-type"} and "filename=" in h.get("value",""):
                                        filename = h["value"].split("filename=")[-1].strip().strip('"')
                                pdf_attachments.append({"filename": filename, "content": content})
                    # Yield the processed email data
                    yield {
                        "from_email": from_email,
                        "to_email": _to_email,
                        "subject": subject,
                        "page_content": body,
                        "pdf_attachments": pdf_attachments,  # NEW
                        "id": process_message["id"],
                        "thread_id": process_message["threadId"],
                        "send_time": parsed_time.isoformat(),
                    }
                    count += 1
                    
            except Exception as e:
                logger.warning(f"Failed to process message {message['id']}: {str(e)}")

        logger.info(f"Found {count} emails to process out of {len(messages)} total messages.")
    
    except Exception as e:
        logger.error(f"Error accessing Gmail API: {str(e)}")
        # Fall back to mock implementation
        mock_email = {
            "from_email": "sender@example.com",
            "to_email": email_address,
            "subject": "Sample Email Subject",
            "page_content": "This is a sample email body for testing the email assistant.",
            "id": "mock-email-id-123",
            "thread_id": "mock-thread-id-123",
            "send_time": datetime.now().isoformat()
        }
        
        yield mock_email

class FetchEmailsInput(BaseModel):
    """
    Input schema for the fetch_emails_tool.
    """
    email_address: str = Field(
        description="Email address to fetch emails for"
    )
    minutes_since: int = Field(
        default=30,
        description="Only retrieve emails newer than this many minutes"
    )

@tool(args_schema=FetchEmailsInput)
def fetch_emails_tool(email_address: str, minutes_since: int = 30) -> str:
    """
    Fetches recent emails from Gmail for the specified email address.
    
    Args:
        email_address: Email address to fetch messages for
        minutes_since: Only retrieve emails newer than this many minutes (default: 30)
        
    Returns:
        String summary of fetched emails
    """
    emails = list(fetch_group_emails(email_address, minutes_since))
    
    if not emails:
        return "No new emails found."
    
    result = f"Found {len(emails)} new emails:\n\n"
    
    for i, email in enumerate(emails, 1):
        if email.get("user_respond", False):
            result += f"{i}. You already responded to this email (Thread ID: {email['thread_id']})\n\n"
            continue
            
        result += f"{i}. From: {email['from_email']}\n"
        result += f"   To: {email['to_email']}\n"
        result += f"   Subject: {email['subject']}\n"
        result += f"   Time: {email['send_time']}\n"
        result += f"   ID: {email['id']}\n"
        result += f"   Thread ID: {email['thread_id']}\n"
        result += f"   Content: {email['page_content'][:200]}...\n\n"
    
    return result

class SendEmailInput(BaseModel):
    """
    Input schema for the send_email_tool.
    """
    email_id: str = Field(
        description="Gmail message ID to reply to. This must be a valid Gmail message ID obtained from the fetch_emails_tool. If you're creating a new email (not replying), you can use any string like 'NEW_EMAIL'."
    )
    response_text: str = Field(
        description="Content of the reply"
    )
    email_address: str = Field(
        description="Current user's email address"
    )
    additional_recipients: Optional[List[str]] = Field(
        default=None,
        description="Optional additional recipients to include"
    )

# Helper function for sending emails
def send_email(
    email_id: str,
    response_text: str,
    email_address: str,
    addn_receipients: Optional[List[str]] = None
) -> bool:
    """
    Send a reply to an existing email thread or create a new email.
    
    Args:
        email_id: Gmail message ID to reply to. If this is not a valid Gmail ID (e.g., when creating a new email),
                 the function will create a new email instead of replying to an existing thread.
        response_text: Content of the reply or new email
        email_address: Current user's email address (the sender)
        addn_receipients: Optional additional recipients
        
    Returns:
        Success flag (True if email was sent)
    """
    if not GMAIL_API_AVAILABLE:
        logger.info("Gmail API not available, simulating email send")
        logger.info(f"Would send: {response_text[:100]}...")
        return True
        
    try:
        # Get Gmail API credentials from environment variables or local files
        creds = get_credentials(
            gmail_token=os.getenv("GMAIL_TOKEN"),
            gmail_secret=os.getenv("GMAIL_SECRET")
        )
        service = build("gmail", "v1", credentials=creds)
        
        try:
            # Try to get the original message to extract headers
            message = service.users().messages().get(userId="me", id=email_id).execute()
            headers = message["payload"]["headers"]
            
            # Extract subject with Re: prefix if not already present
            subject = next(header["value"] for header in headers if header["name"] == "Subject")
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
                
            # Create a reply message
            original_from = next(header["value"] for header in headers if header["name"] == "From")
            
            # Get thread ID from message
            thread_id = message["threadId"]
        except Exception as e:
            logger.warning(f"Could not retrieve original message with ID {email_id}. Error: {str(e)}")
            # If we can't get the original message, create a new message with minimal info
            subject = "Response"
            original_from = "recipient@example.com"  # Will be overridden by user input
            thread_id = None
            
        # Create a message object
        msg = MIMEText(response_text)
        msg["to"] = original_from
        msg["from"] = email_address
        msg["subject"] = subject
        
        # Add additional recipients if specified
        if addn_receipients:
            msg["cc"] = ", ".join(addn_receipients)
            
        # Encode the message
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        
        # Prepare message body
        body = {"raw": raw}
        # Only add threadId if it exists
        if thread_id:
            body["threadId"] = thread_id
            
        # Send the message
        sent_message = (
            service.users()
            .messages()
            .send(
                userId="me",
                body=body,
            )
            .execute()
        )
        
        logger.info(f"Email sent: Message ID {sent_message['id']}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

@tool(args_schema=SendEmailInput)
def send_email_tool(
    email_id: str,
    response_text: str,
    email_address: str,
    additional_recipients: Optional[List[str]] = None
) -> str:
    """
    Send a reply to an existing email thread or create a new email in Gmail.
    
    Args:
        email_id: Gmail message ID to reply to. This should be a valid Gmail message ID obtained from the fetch_emails_tool. 
                 If creating a new email rather than replying, you can use any string identifier like "NEW_EMAIL".
        response_text: Content of the reply or new email
        email_address: Current user's email address (the sender)
        additional_recipients: Optional additional recipients to include
        
    Returns:
        Confirmation message
    """
    try:
        success = send_email(
            email_id,
            response_text,
            email_address,
            addn_receipients=additional_recipients
        )
        if success:
            return f"Email reply sent successfully to message ID: {email_id}"
        else:
            return "Failed to send email due to an API error"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

class CheckCalendarInput(BaseModel):
    """
    Input schema for the check_calendar_tool.
    """
    dates: List[str] = Field(
        description="List of dates to check in DD-MM-YYYY format"
    )

def get_calendar_events(dates: List[str]) -> str:
    """
    Check Google Calendar for events on specified dates.
    
    Args:
        dates: List of dates to check in DD-MM-YYYY format
        
    Returns:
        Formatted calendar events for the specified dates
    """
    if not GMAIL_API_AVAILABLE:
        logger.info("Gmail API not available, simulating calendar check")
        # Fallback: Return mock calendar data for demo/testing purposes
        # In production, this should use the real Google Calendar API
        result = "Calendar events:\n\n"
        for date in dates:
            result += f"Events for {date}:\n"
            result += "  - 9:00 AM - 10:00 AM: Team Meeting\n"
            result += "  - 2:00 PM - 3:00 PM: Project Review\n"
            result += "Available slots: 10:00 AM - 2:00 PM, after 3:00 PM\n\n"
        return result
        
    try:
        # Get Gmail API credentials from environment variables or local files
        creds = get_credentials(
            gmail_token=os.getenv("GMAIL_TOKEN"),
            gmail_secret=os.getenv("GMAIL_SECRET")
        )
        service = build("calendar", "v3", credentials=creds)
        
        result = "Calendar events:\n\n"
        
        for date_str in dates:
            # Parse date string (DD-MM-YYYY)
            day, month, year = date_str.split("-")
            
            # Format start and end times for the API
            start_time = f"{year}-{month}-{day}T00:00:00Z"
            end_time = f"{year}-{month}-{day}T23:59:59Z"
            
            # Call the Calendar API
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_time,
                    timeMax=end_time,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            
            events = events_result.get("items", [])
            
            result += f"Events for {date_str}:\n"
            
            if not events:
                result += "  No events found for this day\n"
                result += "  Available all day\n\n"
                continue
                
            # Process events
            busy_slots = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                
                # Convert to datetime objects
                if "T" in start:  # dateTime format
                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                    
                    # Format for display
                    start_display = start_dt.strftime("%I:%M %p")
                    end_display = end_dt.strftime("%I:%M %p")
                    
                    result += f"  - {start_display} - {end_display}: {event['summary']}\n"
                    busy_slots.append((start_dt, end_dt))
                else:  # all-day event
                    result += f"  - All day: {event['summary']}\n"
                    busy_slots.append(("all-day", "all-day"))
            
            # Calculate available slots
            if "all-day" in [slot[0] for slot in busy_slots]:
                result += "  Available: No availability (all-day events)\n\n"
            else:
                # Sort busy slots by start time
                busy_slots.sort(key=lambda x: x[0])
                
                # Define working hours (9 AM to 5 PM)
                # Note: Working hours are currently hardcoded for simplicity
                # In production, this could be made configurable per user/organization
                work_start = datetime(
                    year=int(year), 
                    month=int(month), 
                    day=int(day), 
                    hour=9, 
                    minute=0
                )
                work_end = datetime(
                    year=int(year), 
                    month=int(month), 
                    day=int(day), 
                    hour=17, 
                    minute=0
                )
                
                # Calculate available slots
                available_slots = []
                current = work_start
                
                for start, end in busy_slots:
                    if current < start:
                        available_slots.append((current, start))
                    current = max(current, end)
                
                if current < work_end:
                    available_slots.append((current, work_end))
                
                # Format available slots
                if available_slots:
                    result += "  Available: "
                    for i, (start, end) in enumerate(available_slots):
                        start_display = start.strftime("%I:%M %p")
                        end_display = end.strftime("%I:%M %p")
                        result += f"{start_display} - {end_display}"
                        if i < len(available_slots) - 1:
                            result += ", "
                    result += "\n\n"
                else:
                    result += "  Available: No availability during working hours\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking calendar: {str(e)}")
        # Return mock data in case of error
        result = "Calendar events (mock due to error):\n\n"
        for date in dates:
            result += f"Events for {date}:\n"
            result += "  - 9:00 AM - 10:00 AM: Team Meeting\n"
            result += "  - 2:00 PM - 3:00 PM: Project Review\n"
            result += "Available slots: 10:00 AM - 2:00 PM, after 3:00 PM\n\n"
        return result

@tool(args_schema=CheckCalendarInput)
def check_calendar_tool(dates: List[str]) -> str:
    """
    Check Google Calendar for events on specified dates.
    
    Args:
        dates: List of dates to check in DD-MM-YYYY format
        
    Returns:
        Formatted calendar events for the specified dates
    """
    try:
        events = get_calendar_events(dates)
        return events
    except Exception as e:
        return f"Failed to check calendar: {str(e)}"

class ScheduleMeetingInput(BaseModel):
    """
    Input schema for the schedule_meeting_tool.
    """
    attendees: List[str] = Field(
        description="Email addresses of meeting attendees"
    )
    title: str = Field(
        description="Meeting title/subject"
    )
    start_time: str = Field(
        description="Meeting start time in ISO format (YYYY-MM-DDTHH:MM:SS)"
    )
    end_time: str = Field(
        description="Meeting end time in ISO format (YYYY-MM-DDTHH:MM:SS)"
    )
    organizer_email: str = Field(
        description="Email address of the meeting organizer"
    )
    timezone: str = Field(
        default="America/Los_Angeles",
        description="Timezone for the meeting"
    )

def send_calendar_invite(
    attendees: List[str],
    title: str,
    start_time: str,
    end_time: str,
    organizer_email: str,
    timezone: str = "America/Los_Angeles"
) -> bool:
    """
    Schedule a meeting with Google Calendar and send invites.
    
    Args:
        attendees: Email addresses of meeting attendees
        title: Meeting title/subject
        start_time: Meeting start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        end_time: Meeting end time in ISO format (YYYY-MM-DDTHH:MM:SS)
        organizer_email: Email address of the meeting organizer
        timezone: Timezone for the meeting
        
    Returns:
        Success flag (True if meeting was scheduled)
    """
    if not GMAIL_API_AVAILABLE:
        logger.info("Gmail API not available, simulating calendar invite")
        logger.info(f"Would schedule: {title} from {start_time} to {end_time}")
        logger.info(f"Attendees: {', '.join(attendees)}")
        return True
        
    try:
        # Get Gmail API credentials from environment variables or local files
        creds = get_credentials(
            gmail_token=os.getenv("GMAIL_TOKEN"),
            gmail_secret=os.getenv("GMAIL_SECRET")
        )
        service = build("calendar", "v3", credentials=creds)
        
        # Create event details
        event = {
            "summary": title,
            "start": {
                "dateTime": start_time,
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_time,
                "timeZone": timezone,
            },
            "attendees": [{"email": email} for email in attendees],
            "organizer": {
                "email": organizer_email,
                "self": True,
            },
            "reminders": {
                "useDefault": True,
            },
            "sendUpdates": "all",  # Send email notifications to attendees
        }
        
        # Create the event
        event = service.events().insert(calendarId="primary", body=event).execute()
        
        logger.info(f"Meeting created: {event.get('htmlLink')}")
        return True
        
    except Exception as e:
        logger.error(f"Error scheduling meeting: {str(e)}")
        return False

@tool(args_schema=ScheduleMeetingInput)
def schedule_meeting_tool(
    attendees: List[str],
    title: str,
    start_time: str,
    end_time: str,
    organizer_email: str,
    timezone: str = "America/Los_Angeles"
) -> str:
    """
    Schedule a meeting with Google Calendar and send invites.
    
    Args:
        attendees: Email addresses of meeting attendees
        title: Meeting title/subject
        start_time: Meeting start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        end_time: Meeting end time in ISO format (YYYY-MM-DDTHH:MM:SS)
        organizer_email: Email address of the meeting organizer
        timezone: Timezone for the meeting (default: America/Los_Angeles)
        
    Returns:
        Success or failure message
    """
    try:
        success = send_calendar_invite(
            attendees,
            title,
            start_time,
            end_time,
            organizer_email,
            timezone
        )
        
        if success:
            return f"Meeting '{title}' scheduled successfully from {start_time} to {end_time} with {len(attendees)} attendees"
        else:
            return "Failed to schedule meeting"
    except Exception as e:
        return f"Error scheduling meeting: {str(e)}"
    
def mark_as_read(
    message_id,
    gmail_token: str | None = None,
    gmail_secret: str | None = None,
):
    creds = get_credentials(gmail_token, gmail_secret)

    service = build("gmail", "v1", credentials=creds)
    service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()