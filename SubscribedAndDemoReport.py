import requests
from bs4 import BeautifulSoup as bs
import json

import os

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

cache = json.loads(os.environ.get('cache'))
sender = json.loads(os.environ.get('SENDER'))
receiver = os.environ.get('RECEIVER')
trigger_type = os.environ.get('triggerType')

cacheAPI = cache['cacheAPI']
cacheURL = cache['cacheURL']

headers = {
    "Authorization": f"Bearer {cacheAPI}",
    "Content-Type": "text/plain"
}

cacheResponse = requests.get(cacheURL, headers=headers)
print(cacheResponse.status_code)

SENDER_EMAIL = sender['email']
SENDER_PASSWORD = sender['pass']
RECEIVER_EMAIL = [receiver]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

def send_email(template,title):

    # Create a secure SSL context
    context = ssl.create_default_context()

    try:
        # Using a 'with' statement ensures the connection is automatically closed
        print(f"Connecting to {SMTP_SERVER} on port {SMTP_PORT}...")

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:

            print("Logging in...")
            server.login(SENDER_EMAIL, SENDER_PASSWORD)

            print("Sending email...")

            i = 0
            for email in RECEIVER_EMAIL:

              # Create the Email Message
              message = MIMEMultipart("alternative")
              message["Subject"] = title
              message["From"] = f'IPO REPORT <{SENDER_EMAIL}>'
              message["To"] = email

              # Attach the HTML body to the message
              part = MIMEText(template.format(email) if trigger_type.lower() == "subscribed" else template, "html")
              message.attach(part)

              server.sendmail(SENDER_EMAIL, email, message.as_string())
              i+=1

            print(f"{i} email{'s' if i>0 else ''} sent successfully!")

    except smtplib.SMTPAuthenticationError:
        print("\nAUTHENTICATION FAILED")

    except Exception as e:
        print(f"\nAn error occurred: {e}")



if trigger_type.lower() == "demo":
  content = bs(cache.content, "html.parser")
  updateBtn = content.find('a', id = "updateBtn")
  updateBtn.string = "Subscribe to Request Updated Report"
  updateBtn['href'] = "https://iporeports.webflow.com/#subscribe"
  content = str(content)
else:
  content = cache.text

send_email(content,"Thank you for Subscribing! Here is today's IPO Report." if trigger_type.lower() == 'subscribed' else "Here is your Demo IPO Report." )
