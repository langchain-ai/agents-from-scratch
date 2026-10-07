"""Tool prompt templates for Gmail integration."""

# Gmail tools prompt for insertion into agent system prompts
GMAIL_TOOLS_PROMPT = """
1. fetch_emails_tool(email_address, minutes_since) - Fetch recent emails from Gmail
2. send_email_tool(email_id, response_text, email_address, additional_recipients) - Send a reply to an email thread
3. check_calendar_tool(dates) - Check Google Calendar availability for specific dates
4. schedule_meeting_tool(attendees, title, start_time, end_time, organizer_email, timezone) - Schedule a meeting on calendar without sending invites (send_email_tool must be used to notify attendees)
5. triage_email(ignore, notify, respond) - Triage emails into one of three categories
6. Done - E-mail has been sent
"""

# Combined tools prompt (default + Gmail) for full integration
COMBINED_TOOLS_PROMPT = """
1. fetch_emails_tool(email_address, minutes_since) - Fetch recent emails from Gmail
2. send_email_tool(email_id, response_text, email_address, additional_recipients) - Send a reply to an email thread
3. check_calendar_tool(dates) - Check Google Calendar availability for specific dates
4. schedule_meeting_tool(attendees, title, start_time, end_time, organizer_email, timezone) - Schedule a meeting on calendar without sending invites (send_email_tool must be used to notify attendees)
5. write_email(to, subject, content) - Draft emails to specified recipients
6. triage_email(ignore, notify, respond) - Triage emails into one of three categories
7. check_calendar_availability(day) - Check available time slots for a given day
8. Done - E-mail has been sent
"""