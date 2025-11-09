import json
import os

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sender = json.loads(os.environ.get('SENDER'))
receiver = json.loads(os.environ.get('RECEIVER'))

SENDER_EMAIL = sender['email']
SENDER_PASSWORD =sender['pass']
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
              part = MIMEText(template, "html")
              message.attach(part)

              server.sendmail(SENDER_EMAIL, email, message.as_string())
              i+=1

            print(f"{i} email{'s' if i>0 else ''} sent successfully!")

    except smtplib.SMTPAuthenticationError:
        print("\nAUTHENTICATION FAILED")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

content = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
    <meta name="x-apple-disable-message-reformatting">
    <color-scheme content="light dark">
    <supported-color-schemes>light dark</supported-color-schemes>
    <title>Unsubscribe Confirmation</title>
    <!--[if mso]>
    <xml>
        <o:OfficeDocumentSettings>
            <o:PixelsPerInch>96</o:PixelsPerInch>
        </o:OfficeDocumentSettings>
    </xml>
    <style>
        td,th,div,p,a,h1,h2,h3,h4,h5,h6 {font-family: "Helvetica Neue", Helvetica, Arial, sans-serif !important;}
    </style>
    <![endif]-->
    <style type="text/css">
        /* Basic Resets */
        body { margin: 0 !important; padding: 0 !important; width: 100% !important; -webkit-text-size-adjust: 100% !important; -ms-text-size-adjust: 100% !important; -webkit-font-smoothing: antialiased !important; }
        img { border: 0 !important; outline: none !important; display: block !important; }
        table { border-collapse: collapse; mso-table-lspace: 0px; mso-table-rspace: 0px; }
        td { border-collapse: collapse; mso-line-height-rule: exactly; }
        a, span { mso-line-height-rule: exactly; }
        .ExternalClass * { line-height: 100%; }

        /* Mobile Optimizations */
        @media only screen and (max-width:600px) {
            .main_table { width: 100% !important; }
            .wrapper { padding: 20px 20px !important; }
            .mobile_center { text-align: center !important; }
        }
        /* Dark Mode Handling (Optional - keeps it BW in dark mode too) */
        @media (prefers-color-scheme: dark) {
            .dark_bg { background-color: #1a1a1a !important; }
            .dark_text { color: #ffffff !important; }
            .dark_border { border-color: #333333 !important; }
        }
    </style>
</head>
<body style="margin:0; padding:0; background-color:#f4f4f4; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif;">
    <center>
        <!-- Outer Wrapper -->
        <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#f4f4f4;">
            <tr>
                <td align="center" valign="top" style="padding: 40px 0;">
                    <!-- Main Container -->
                    <table class="main_table" width="600" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:600px; max-width:600px; background-color:#ffffff; margin:0 auto;">
                        <tr>
                            <td class="wrapper" style="padding: 40px 50px;">
                                <!-- Logo/Brand Area (Text based for simplicity) -->
                                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                                    <tr>
                                        <td align="left" style="padding-bottom: 30px;">
                                            <span style="color:#000000; font-size: 20px; font-weight: 700; letter-spacing: -0.5px; text-decoration:none;">IPO REPORTS</span>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Main Headline -->
                                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                                    <tr>
                                        <td align="left" style="color:#000000; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 32px; line-height: 40px; font-weight: 700; padding-bottom: 20px;">
                                            We're sorry to see you go.
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="left" style="color:#333333; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; line-height: 26px; padding-bottom: 30px;">
                                            You have been successfully unsubscribed from our service. You won't receive any further emails regarding Reports.
                                        </td>
                                    </tr>
                                </table>

                                <!-- Simple Line Divider -->
                                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                                    <tr>
                                        <td align="center" style="padding-bottom: 30px;">
                                            <div style="height: 1px; width: 100%; background-color: #000000; line-height: 1px; font-size: 1px;">&nbsp;</div>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Followback Section -->
                                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                                    <tr>
                                        <td align="left" style="color:#333333; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; line-height: 26px; padding-bottom: 25px;">
                                            Was this a mistake? If you changed your mind, you can resubscribe anytime by visiting our website below.
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="left">
                                            <!-- Button -->
                                            <table border="0" cellspacing="0" cellpadding="0" role="presentation">
                                                <tr>
                                                    <td align="center" bgcolor="#000000" style="border-radius: 4px; background-color: #000000;">
                                                        <!--[if mso]>
                                                        <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="https://iporeports.webflow.com" style="height:50px;v-text-anchor:middle;width:200px;" arcsize="8%" stroke="f" fillcolor="#000000">
                                                        <w:anchorlock/>
                                                        <center>
                                                        <![endif]-->
                                                            <a href="https://iporeports.webflow.com" target="_blank" style="background-color:#000000; border-radius: 4px; color:#ffffff; display:inline-block; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; font-weight: bold; line-height: 50px; text-align:center; text-decoration:none; width: 200px; -webkit-text-size-adjust:none;">
                                                                Return to Website
                                                            </a>
                                                        <!--[if mso]>
                                                        </center>
                                                        </v:roundrect>
                                                        <![endif]-->
                                                    </td>
                                                </tr>
                                            </table>
                                            <!-- End Button -->
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <!-- Simple Footer -->
                         <tr>
                            <td style="background-color: #000000; padding: 20px 50px;">
                                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                                    <tr>
                                        <td align="center" style="color:#999999; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 12px; line-height: 18px;">
                                            
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </center>
</body>
</html>
"""

send_email(content,"You have successfuly unsubscribed")
