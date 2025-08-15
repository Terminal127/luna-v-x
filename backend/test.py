import json
import base64
import requests

def send_email(to_email: str, subject: str, body: str):
    """
    Sends an email via Gmail API using a saved Google OAuth access token.

    Args:
        to_email (str): Recipient's email address.
        subject (str): Email subject.
        body (str): Email body content.

    Returns:
        dict: JSON response from Gmail API.
    """

    # ---- Helper: Read access token from saved file ----
    def get_access_token():
        with open("/home/anubhav/courses/luna-version-x/frontend/saved-tokens/google_token.json", "r") as f:
            data = json.load(f)
        return data["accessToken"]

    # ---- Helper: Build raw email and encode ----
    def create_raw_email():
        from_email = "terminalishere127@gmail.com"  # Your Gmail
        message = f"From: Terminal Terminal <{from_email}>\n" \
                  f"To: {to_email}\n" \
                  f"Subject: {subject}\n\n" \
                  f"{body}"
        encoded_message = base64.urlsafe_b64encode(message.encode("utf-8")).decode("utf-8")
        return encoded_message

    # ---- Main sending logic ----
    access_token = get_access_token()
    raw_email = create_raw_email()

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {"raw": raw_email}

    response = requests.post(url, headers=headers, json=payload)

    # Return the Gmail API JSON response
    return response.json()

# Example usage:
if __name__ == "__main__":
    resp = send_email(
        to_email="distortion8420@gmail.com",
        subject="python test 1",
        body="Hello! Testing the python fucntion."
    )
    print(json.dumps(resp, indent=2))
