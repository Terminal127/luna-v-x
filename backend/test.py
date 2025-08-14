import json
import requests
import base64
import html
import argparse

def read_gmail_messages(top=5):
    """Main function to read Gmail messages with all helper functions defined inside"""

    def decode_base64_url(data):
        """Decode base64url-encoded data"""
        # Add padding if needed
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)

        # Replace URL-safe characters
        data = data.replace('-', '+').replace('_', '/')

        try:
            return base64.b64decode(data).decode('utf-8')
        except:
            return "[Unable to decode content]"

    def extract_message_body(payload):
        """Extract the message body from Gmail API payload"""
        body = ""

        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body += decode_base64_url(part['body']['data'])
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    html_content = decode_base64_url(part['body']['data'])
                    # You might want to strip HTML tags here
                    body += f"\n[HTML Content]: {html_content[:200]}..." if len(html_content) > 200 else f"\n[HTML Content]: {html_content}"
                elif 'parts' in part:  # Nested parts
                    body += extract_message_body(part)

        # Handle simple messages (not multipart)
        elif 'data' in payload.get('body', {}):
            body = decode_base64_url(payload['body']['data'])

        return body

    def get_attachments_info(payload):
        """Extract attachment information"""
        attachments = []

        def process_parts(parts):
            for part in parts:
                if part.get('filename'):
                    attachment_info = {
                        'filename': part['filename'],
                        'mimeType': part['mimeType'],
                        'size': part['body'].get('size', 0)
                    }
                    attachments.append(attachment_info)

                if 'parts' in part:
                    process_parts(part['parts'])

        if 'parts' in payload:
            process_parts(payload['parts'])

        return attachments

    # Main execution starts here
    # Read tokens from file
    with open("/home/anubhav/courses/luna-version-x/frontend/saved-tokens/google_token_terminalishere127_at_gmail_com.json", "r") as f:
        data = json.load(f)

    access_token = data["accessToken"]

    # Step 1: Get list of messages
    list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    params = {
        "maxResults": top,
        "labelIds": "INBOX"
    }

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    list_response = requests.get(list_url, headers=headers, params=params)

    if list_response.status_code != 200:
        print("Error fetching messages:", list_response.status_code, list_response.text)
        return

    messages = list_response.json().get("messages", [])
    print(f"Found {len(messages)} messages\n")

    # Step 2: Fetch detailed information for each message
    for i, msg in enumerate(messages, 1):
        msg_id = msg["id"]

        # Use 'full' format to get complete message data
        detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
        detail_params = {"format": "full"}

        detail_response = requests.get(detail_url, headers=headers, params=detail_params)

        if detail_response.status_code != 200:
            print(f"Error fetching message {i} details:", detail_response.status_code, detail_response.text)
            continue

        msg_data = detail_response.json()

        # Extract all available headers
        headers_list = msg_data.get("payload", {}).get("headers", [])

        # Create a dictionary of headers for easy access
        email_headers = {h["name"]: h["value"] for h in headers_list}

        # Extract key information
        subject = email_headers.get("Subject", "(No Subject)")
        sender = email_headers.get("From", "(No Sender)")
        recipient = email_headers.get("To", "(No Recipient)")
        date = email_headers.get("Date", "(No Date)")
        cc = email_headers.get("Cc", "")
        bcc = email_headers.get("Bcc", "")
        reply_to = email_headers.get("Reply-To", "")
        message_id = email_headers.get("Message-ID", "")

        # Extract message body
        payload = msg_data.get("payload", {})
        body = extract_message_body(payload)

        # Get attachments info
        attachments = get_attachments_info(payload)

        # Get snippet
        snippet = msg_data.get("snippet", "").strip()

        # Get labels
        label_ids = msg_data.get("labelIds", [])

        # Get thread ID
        thread_id = msg_data.get("threadId", "")

        # Print comprehensive information
        print(f"{'='*80}")
        print(f"MESSAGE {i} - ID: {msg_id}")
        print(f"{'='*80}")
        print(f"📧 Subject: {subject}")
        print(f"👤 From: {sender}")
        print(f"👥 To: {recipient}")
        if cc:
            print(f"📋 CC: {cc}")
        if bcc:
            print(f"📋 BCC: {bcc}")
        if reply_to:
            print(f"↩️  Reply-To: {reply_to}")
        print(f"📅 Date: {date}")
        print(f"🆔 Message ID: {message_id}")
        print(f"🧵 Thread ID: {thread_id}")
        print(f"🏷️  Labels: {', '.join(label_ids)}")

        print(f"\n📄 SNIPPET:")
        print(f"{snippet}")

        print(f"\n📃 FULL BODY:")
        print("-" * 40)
        if body.strip():
            print(body[:1000] + "..." if len(body) > 1000 else body)  # Limit body length for readability
        else:
            print("[No plain text body found]")

        if attachments:
            print(f"\n📎 ATTACHMENTS ({len(attachments)}):")
            for att in attachments:
                print(f"  • {att['filename']} ({att['mimeType']}, {att['size']} bytes)")

        # Show additional headers (optional)
        print(f"\n📋 ALL HEADERS:")
        print("-" * 40)
        for header_name, header_value in email_headers.items():
            if header_name not in ['Subject', 'From', 'To', 'Date', 'Cc', 'Bcc', 'Reply-To', 'Message-ID']:
                print(f"{header_name}: {header_value}")

        print("\n" + "="*80 + "\n")

    print("✅ Email extraction completed!")

if __name__ == "__main__":
    read_gmail_messages(top=1)
