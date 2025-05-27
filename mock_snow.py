import requests
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import base64
import google.generativeai as genai
import logging
import traceback
import time
from google.api_core import exceptions, retry
from dotenv import load_dotenv
from email.mime.text import MIMEText
from html.parser import HTMLParser

# Load environment variables
load_dotenv()

# Configuration from .env
SNOW_URL = os.getenv("SNOW_URL")
SNOW_USER = os.getenv("SNOW_USER")
SNOW_PASS = os.getenv("SNOW_PASS")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
MANAGER_EMAIL = os.getenv("MANAGER_EMAIL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validate environment variables
required_vars = ["SNOW_URL", "SNOW_USER", "SNOW_PASS", "GMAIL_ADDRESS", "MANAGER_EMAIL", "GEMINI_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

# Set base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Logging setup
LOG_FILE = os.path.join(BASE_DIR, "ticket_log.txt")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s: %(message)s')

def log_action(message):
    logging.info(message)
    print(message)

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    creds = None
    token_path = os.path.join(BASE_DIR, 'token.pickle')
    creds_path = os.path.join(BASE_DIR, 'credentials.json')

    try:
        log_action("Attempting to set up Gmail service...")
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                log_action("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    log_action(f"Missing {creds_path}. Download from Google Cloud Console.")
                    return None
                log_action("Initiating OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        service = build('gmail', 'v1', credentials=creds)
        log_action("Gmail service initialized successfully.")
        return service
    except Exception as e:
        log_action(f"Error setting up Gmail service: {e}")
        traceback.print_exc()
        return None

# Gemini API setup
try:
    log_action("Setting up Gemini API...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    log_action("Gemini API initialized successfully.")
except Exception as e:
    log_action(f"Error setting up Gemini API: {e}")
    traceback.print_exc()
    model = None

# Retry decorator for Gemini API
@retry.Retry(predicate=retry.if_exception_type(exceptions.ResourceExhausted), initial=46, maximum=120, multiplier=2)
def call_gemini_with_retry(prompt):
    return model.generate_content(prompt)

def analyze_email(email_content):
    if not model:
        log_action("Gemini model not initialized, skipping email analysis")
        return {'action': 'ignore', 'priority': 'normal', 'table': 'incident', 'status': 'New'}

    if not email_content or email_content.strip() == "":
        log_action("Empty email content, returning ignore action")
        return {'action': 'ignore', 'priority': 'normal', 'table': 'incident', 'status': 'New'}

    # Bypass Gemini for explicit change requests
    if email_content.lower().startswith("change:"):
        log_action("Detected 'Change:' in email, assigning create_change action")
        return {'action': 'create_change', 'priority': 'normal', 'table': 'change_request', 'status': 'New'}

    # Detect update commands (e.g., "Set ticket INC0010111 to Resolved")
    if "set ticket" in email_content.lower():
        import re
        match = re.search(r"set ticket (\w{3}\d{7}) to (\w+)", email_content.lower())
        if match:
            ticket_number = match.group(1).upper()
            status = match.group(2).capitalize()
            comment_match = re.search(r"with comment: (.+)", email_content, re.IGNORECASE)
            comment = comment_match.group(1) if comment_match else "Updated via email"
            state_map = {
                "New": "1", "In Progress": "2", "On Hold": "3",
                "Resolved": "6", "Closed": "7", "Cancelled": "8"
            }
            if status in state_map:
                log_action(f"Detected update for ticket {ticket_number} to {status}")
                return {
                    'action': 'update_ticket',
                    'ticket_number': ticket_number,
                    'table': 'incident' if ticket_number.startswith('INC') else 'change_request',
                    'status': status,
                    'comment': comment
                }
            else:
                log_action(f"Invalid status {status} for ticket {ticket_number}")
                return {'action': 'ignore', 'priority': 'normal', 'table': 'incident', 'status': 'New'}

    prompt = f"""
    Analyze this email content: "{email_content}"
    Return a JSON object with:
    - action: One of 'create_incident', 'create_change', 'set_new', 'set_in_progress', 'set_on_hold', 'set_resolved', 'set_closed', 'set_cancelled', 'approve', 'deny', 'ignore'
    - priority: 'high' or 'normal'
    - table: 'incident' or 'change_request'
    - status: 'New', 'In Progress', 'On Hold', 'Resolved', 'Closed', 'Cancelled'
    Examples:
    - "Urgent: Printer broken" → {{"action": "create_incident", "priority": "high", "table": "incident", "status": "New"}}
    - "Change: Install software" → {{"action": "create_change", "priority": "normal", "table": "change_request", "status": "New"}}
    - "Working on it" → {{"action": "set_in_progress", "priority": "normal", "table": "incident", "status": "In Progress"}}
    """
    try:
        log_action("Analyzing email content with Gemini...")
        response = call_gemini_with_retry(prompt)
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:].rstrip('```').strip()
        elif text.startswith('```'):
            text = text[3:].rstrip('```').strip()
        result = json.loads(text)
        log_action(f"Email analysis result: {result}")
        return result
    except json.JSONDecodeError as e:
        log_action(f"JSON parsing error: {e}. Response: {text}")
        return {'action': 'ignore', 'priority': 'normal', 'table': 'incident', 'status': 'New'}
    except exceptions.ResourceExhausted as e:
        log_action(f"Gemini quota exceeded: {e}")
        return {'action': 'ignore', 'priority': 'normal', 'table': 'incident', 'status': 'New'}
    except Exception as e:
        log_action(f"Error analyzing email: {e}")
        traceback.print_exc()
        return {'action': 'ignore', 'priority': 'normal', 'table': 'incident', 'status': 'New'}

def create_ticket(table, subject, description, priority):
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "short_description": subject,
            "description": description,
            "assignment_group": "287ebd7da9fe198100f92cc8d1d2154e",
            "urgency": "1" if priority == "high" else "2",
            "impact": "1" if priority == "high" else "2",
            "state": "1"
        }
        if table == "change_request":
            data["approval"] = "requested"
        url = f"{SNOW_URL}/{table}"
        log_action(f"Creating {table} ticket: {subject}")
        response = requests.post(url, auth=(SNOW_USER, SNOW_PASS), headers=headers, json=data)
        if response.status_code == 201:
            result = response.json()['result']
            log_action(f"Ticket Created: {result['number']} (ID: {result['sys_id']})")
            return result['sys_id'], result['number']
        else:
            log_action(f"Error creating {table} ticket: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        log_action(f"Error creating ticket: {e}")
        traceback.print_exc()
        return None, None

def update_ticket(table, ticket_number, status, comment, priority='normal'):
    try:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        state_map = {
            "New": "1", "In Progress": "2", "On Hold": "3",
            "Resolved": "6", "Closed": "7", "Cancelled": "8"
        }
        data = {
            "state": state_map.get(status, "1"),
            "comments": comment,
            "priority": "1" if priority == "high" else "4"
        }
        if table == "change_request" and status == "In Progress":
            data["approval"] = "approved"
        url = f"{SNOW_URL}/{table}/{ticket_number}"
        log_action(f"Updating {table} ticket {ticket_number} to {status}")
        response = requests.patch(url, auth=(SNOW_USER, SNOW_PASS), headers=headers, json=data)
        if response.status_code == 200:
            log_action(f"Updated {table} ticket {ticket_number} to {status}")
        else:
            log_action(f"Error updating {table} ticket {ticket_number}: {response.status_code} - {response.text}")
    except Exception as e:
        log_action(f"Error updating ticket: {e}")
        traceback.print_exc()

def send_approval_email(service, ticket_number, subject, description):
    try:
        log_action(f"Preparing approval email for ticket {ticket_number} to {MANAGER_EMAIL}")
        message = MIMEText(
            f"Please review this change request:\n"
            f"Title: {subject}\n"
            f"Description: {description}\n\n"
            f"Reply 'Approved' or 'Denied' to this email."
        )
        message['From'] = GMAIL_ADDRESS
        message['To'] = MANAGER_EMAIL
        message['Subject'] = f"Approval Needed for Ticket {ticket_number}"
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        log_action(f"Sending approval email for ticket {ticket_number}")
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        log_action(f"Sent approval email for ticket {ticket_number} to {MANAGER_EMAIL}")
    except Exception as e:
        log_action(f"Error sending approval email: {e}")
        traceback.print_exc()

def process_emails():
    service = get_gmail_service()
    if not service:
        log_action("Failed to initialize Gmail service, exiting.")
        return
    try:
        log_action("Fetching emails...")
        results = service.users().messages().list(userId='me', q=f"to:{GMAIL_ADDRESS} is:unread").execute()
        messages = results.get('messages', [])
        if not messages:
            log_action("No unread emails found to process.")
            return
        log_action(f"Found {len(messages)} unread emails to process.")
        ticket_ids_file = os.path.join(BASE_DIR, 'ticket_ids.txt')

        for i, msg in enumerate(messages):
            msg_id = msg['id']
            log_action(f"Processing email ID: {msg_id}")
            msg_detail = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            headers = msg_detail['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), '')
            snippet = msg_detail.get('snippet', '')
            log_action(f"Fetched email subject: {subject}")

            body = ''
            parts = msg_detail['payload'].get('parts', [])
            if parts:
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
                    elif part['mimeType'] == 'text/html':
                        data = part['body'].get('data')
                        if data:
                            class HTMLStripper(HTMLParser):
                                def __init__(self):
                                    super().__init__()
                                    self.text = []
                                def handle_data(self, data):
                                    self.text.append(data.strip())
                                def get_text(self):
                                    return ' '.join(self.text).strip()
                            stripper = HTMLStripper()
                            stripper.feed(base64.urlsafe_b64decode(data).decode('utf-8'))
                            body = stripper.get_text()
                            if body:
                                break
            else:
                body = snippet
            log_action(f"Email subject: {subject}, body: {body[:50]}...")

            analysis = analyze_email(body)
            action = analysis.get('action')
            priority = analysis.get('priority')
            table = analysis.get('table')
            status = analysis.get('status')

            if action == "ignore":
                log_action(f"Ignored email: {subject}")
            elif action == "create_incident" or action == "create_change":
                ticket_id, ticket_number = create_ticket(table, subject, body, priority)
                if ticket_id:
                    with open(ticket_ids_file, 'a') as f:
                        f.write(subject + '\n')
                    if table == "change_request":
                        send_approval_email(service, ticket_number, subject, body)
            elif action == "update_ticket":
                ticket_number = analysis.get('ticket_number')
                status = analysis.get('status')
                comment = analysis.get('comment')
                update_ticket(table, ticket_number, status, comment, priority)
            elif action in ["set_new", "set_in_progress", "set_on_hold", "set_resolved", "set_closed", "set_cancelled"]:
                log_action(f"Update action {action} requested but ticket ID extraction not implemented for email: {subject}")
            elif action in ["approve", "deny"]:
                log_action(f"Approval action '{action}' received for email: {subject}")
            else:
                log_action(f"Unknown action '{action}' for email: {subject}")

            log_action(f"Marking email {msg_id} as read.")
            service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()

            if i < len(messages) - 1:
                log_action("Waiting 5 seconds to avoid Gemini rate limit...")
                time.sleep(5)

    except Exception as e:
        log_action(f"Error processing emails: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    log_action("Starting ServiceNowAgent...")
    process_emails()