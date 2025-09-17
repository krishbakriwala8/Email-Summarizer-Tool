import os
import openai
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email

# Load .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def fetch_recent_emails(service, max_results=5):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread', maxResults=max_results).execute()
    messages = results.get('messages', [])
    email_bodies = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='raw').execute()
        msg_str = base64.urlsafe_b64decode(msg_data['raw'].encode('ASCII'))
        mime_msg = email.message_from_bytes(msg_str)
        for part in mime_msg.walk():
            if part.get_content_type() == 'text/plain':
                email_bodies.append(part.get_payload())
                break
    return email_bodies

def summarize_text(text):
    prompt = f"Summarize this email in 2 lines with any action points:\n\n{text}"
    response = openai.ChatCompletion.create(
        model="gpt-4",  # or "gpt-3.5-turbo"
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response['choices'][0]['message']['content'].strip()

def main():
    print("Authenticating Gmail...")
    service = authenticate_gmail()
    print("Fetching emails...")
    emails = fetch_recent_emails(service)

    if not emails:
        print("No unread emails found.")
        return

    print("\n--- Email Summaries ---")
    for i, email_text in enumerate(emails):
        try:
            summary = summarize_text(email_text)
            print(f"\nEmail {i+1}:\n{summary}\n")
        except Exception as e:
            print(f"Error summarizing email {i+1}: {e}")

if __name__ == '__main__':
    main()
