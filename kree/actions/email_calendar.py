import os
import smtplib
import imaplib
import email
from email.message import EmailMessage
from pathlib import Path
import json
from datetime import datetime

from memory.config_manager import load_email_settings

def _get_drafts_path() -> Path:
    from memory.config_manager import BASE_DIR
    return BASE_DIR / "memory" / "drafts.txt"

def _get_calendar_path() -> Path:
    from memory.config_manager import BASE_DIR
    return BASE_DIR / "memory" / "calendar.json"

def read_inbox(max_emails: int = 5) -> str:
    settings = load_email_settings()
    if settings.get("USE_MOCK_EMAIL", True):
        return (
            f"MOCK INBOX (Showing top {max_emails} unread):\n"
            "1. From 'Mark (Boss)' - Subject: 'Re: V3 Deployment' - Snippet: 'Looks great, let's ship it!'\n"
            "2. From 'GitHub' - Subject: 'Security Alert' - Snippet: 'Dependabot found 1 vulnerability in...'\n"
            "3. From 'Google Calendar' - Subject: 'Upcoming: Sync at 2pm' - Snippet: 'Meeting starts in 30 mins.'\n"
        )
    
    # Real IMAP logic
    user = settings.get("email_address")
    password = settings.get("app_password")
    imap_server = settings.get("imap_server")
    
    if not user or not password:
        return "ERROR: Real email is enabled, but credentials are not configured in email_settings.json."
    
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(user, password)
        mail.select('inbox')
        
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            return "ERROR: Failed to search inbox."
            
        email_ids = messages[0].split()
        if not email_ids:
            return "Your inbox is clear. 0 unread messages."
            
        recent_ids = email_ids[-max_emails:]
        output = []
        for i, e_id in enumerate(reversed(recent_ids)):
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = email.header.decode_header(msg['Subject'])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    from_ = msg.get('From')
                    output.append(f"{i+1}. From: {from_} - Subject: {subject}")
        mail.logout()
        return "\n".join(output)
    except Exception as e:
        return f"ERROR reading inbox: {e}"

def draft_email(to: str, subject: str, body: str) -> str:
    """Save an email draft for user review before sending."""
    drafts_file = _get_drafts_path()
    drafts_file.parent.mkdir(parents=True, exist_ok=True)
    
    content = f"--- DRAFT EMAIL ---\nTO: {to}\nSUBJECT: {subject}\n\nBODY:\n{body}\n-------------------\n"
    drafts_file.write_text(content, encoding="utf-8")
    
    return f"DRAFT SAVED. Please inform the user: 'I have drafted the email to {to}. Would you like me to send it, or do you want to hear it first?'"

def send_email(to: str, subject: str, body: str) -> str:
    settings = load_email_settings()
    if settings.get("USE_MOCK_EMAIL", True):
        return f"MOCK SUCCESS. Email virtually sent to {to}."
        
    # Real SMTP logic
    user = settings.get("email_address")
    password = settings.get("app_password")
    smtp_server = settings.get("smtp_server")
    
    if not user or not password:
        return "ERROR: Real email is enabled, but credentials are not configured in email_settings.json."

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = user
        msg['To'] = to
        msg.set_content(body)

        with smtplib.SMTP_SSL(smtp_server, 465) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
            
        return f"SUCCESS. Email sent to {to} via {smtp_server}."
    except Exception as e:
        return f"ERROR sending email: {e}"

def schedule_meeting(title: str, datetime_str: str, duration: str = "60 mins") -> str:
    """Mock calendar meeting scheduling saving to memory/calendar.json"""
    cal_file = _get_calendar_path()
    cal_file.parent.mkdir(parents=True, exist_ok=True)
    
    events = []
    if cal_file.exists():
        try:
            data = json.loads(cal_file.read_text(encoding="utf-8"))
            events = data.get("events", [])
        except Exception:
            pass
            
    events.append({
        "title": title,
        "time": datetime_str,
        "duration": duration,
        "created_at": datetime.now().isoformat()
    })
    
    cal_file.write_text(json.dumps({"events": events}, indent=4), encoding="utf-8")
    return f"SUCCESS. Calendar event '{title}' scheduled for {datetime_str}."

def productivity_manager(parameters: dict, response=None, player=None, session_memory=None) -> str:
    """
    Main router for Email/Calendar functions.
    parameters:
        action (str): read_inbox, draft_email, send_email, schedule_meeting
        to (str): Email recipient (for draft_email, send_email)
        subject (str): Email subject (for draft_email, send_email)
        body (str): Email body (for draft_email, send_email)
        title (str): Meeting title (for schedule_meeting)
        time (str): Meeting time (for schedule_meeting)
    """
    action = parameters.get("action", "")
    
    if player:
        player.write_log(f"[Prod] Action: {action}")
    
    if action == "read_inbox":
        return read_inbox()
        
    elif action == "draft_email":
        to = parameters.get("to", "Unknown")
        subject = parameters.get("subject", "No Subject")
        body = parameters.get("body", "")
        return draft_email(to, subject, body)
        
    elif action == "send_email":
        to = parameters.get("to", "Unknown")
        subject = parameters.get("subject", "No Subject")
        body = parameters.get("body", "")
        return send_email(to, subject, body)
        
    elif action == "schedule_meeting":
        title = parameters.get("title", "Meeting")
        time_str = parameters.get("time", "TBD")
        return schedule_meeting(title, time_str)
        
    else:
        return f"ERROR: Unknown productivity action '{action}'"
