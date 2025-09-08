from datetime import datetime
from bs4 import BeautifulSoup as bs
from io import StringIO
from jinja2 import Template
import pandas as pd
import re

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from playwright.sync_api import sync_playwright

import os
import json

# Setup mailing details
sender = json.loads(os.environ.get('SENDER'))
recievers = json.loads(os.environ.get('RECIEVERS'))

SENDER_EMAIL = sender['email'] 
SENDER_PASSWORD = sender['pass']
RECEIVER_EMAIL = ""  
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup as bs

def load_page(url):

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")                         #go and wait till initial HTML get loaded
        page.wait_for_timeout(2000)                                           #wait for 2s
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)") #scroll to bottom
        page.wait_for_timeout(2000)                                           #again wait for 2s
        page.evaluate("() => window.scrollTo(0, 0)")                          #now scroll back to top
        page.wait_for_timeout(5000)                                           #wait for 5s
        html_content = page.content()                                         #load the new updated HTML
        soup = bs(html_content, 'html.parser') 
        browser.close()
        
        return soup



def send_email(template,total):

    # Create the Email Message
    message = MIMEMultipart("alternative")
    message["Subject"] = f"{total} IPOs are live"
    message["From"] = SENDER_EMAIL
    message["To"] = RECEIVER_EMAIL

    # Attach the HTML body to the message
    part = MIMEText(template, "html")
    message.attach(part)

    # Send the Email:
    # Create a secure SSL context
    context = ssl.create_default_context()

    try:
        # Using a 'with' statement ensures the connection is automatically closed
        print(f"Connecting to {SMTP_SERVER} on port {SMTP_PORT}...")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            print("Logging in...")
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            print("Sending email...")
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message.as_string())
            print("Email sent successfully!")

    except smtplib.SMTPAuthenticationError:
        print("\nAUTHENTICATION FAILED")

    except Exception as e:
        print(f"\nAn error occurred: {e}")


# today = datetime.today().date()
today = datetime.strptime("19-08-2025","%d-%m-%Y").date()

#links
urls = json.loads(os.environ.get('URLS'))
dashboard = urls['dashboard']
url = urls['domain']

# Loading dashboard page having JavaScript
hpsoup = load_page(dashboard)

# Extracting:  ipo[Issuer Company, Open, Close]; sub[Issuer Name, Issue Price, sub]; GMP[Issue Price, gmp]
ipo = hpsoup.find('div', id = "ipoTable")
gmp = hpsoup.find('div', id = "gmpTable")
sub = hpsoup.find('div', id = "liveSubscriptionTable")
link = [(url + a['href']) for a in ipo.find('table').find_all('a')]
print(ipo)
ipoTable = pd.read_html(StringIO(str(ipo)))[0]
gmpTable = pd.read_html(StringIO(str(gmp)))[0]
subTable = pd.read_html(StringIO(str(sub)))[0]

ipoTable['link'] = link

#Converting Date to Date objects
ipoTable['Open'] = ipoTable['Open'].apply(lambda x: datetime.strptime(x, '%d-%m-%Y').date())
ipoTable['Close'] = ipoTable['Close'].apply(lambda x: datetime.strptime(x, '%d-%m-%Y').date())

#filter to open ipos only and if ipo table is null end process.
ipoTable = ipoTable[ (ipoTable['Open'] <= today) & (ipoTable['Close'] >= today)]

# Clearing other table's columns
subTable['Issuer Company'] = subTable['Issuer Company'].str.replace(" BSE, NSE",'')       
subTable['Issue Size'] = subTable['Issue Size'].str.replace('₹','').str.replace(" Cr",'') 
subTable['Total Subscription'] = subTable['Total Subscription'].str.replace('x', '')      

#Filtering Other Tables
gmpTableCurrent = gmpTable[ gmpTable['Issuer Company'].isin(ipoTable['Issuer Company'])]
subTableCurrent = subTable[ subTable['Issuer Company'].isin(ipoTable['Issuer Company'])]

gmpTableCurrent.reset_index(level= None, inplace = True, drop = True)
subTableCurrent.reset_index(level = None, inplace = True, drop = True)
ipoTable.reset_index(level = None, inplace = True, drop = True)

#preparing Table[Name, Issue price, Issue size, GMP, Sub, Close] for Active IPOs
ipoTable['IPO Price'] = gmpTableCurrent['IPO Price']
ipoTable['Issue Size'] = subTableCurrent['Issue Size']
ipoTable['GMP'] = gmpTableCurrent['GMP']
ipoTable['Subscribed'] = subTableCurrent['Total Subscription']

#prepare dictionary moreInfo{company : {}}
moreInfo = {}

for company, link in zip(ipoTable['Issuer Company'],ipoTable['link']):

  moreInfo[company] = {}
  details = moreInfo[company]

  # Loading the ipo page
  pgsoup = load_page(link)

  # extracting informations
  financials = pgsoup.find('table', id = 'financialTable')
  objectives = pgsoup.find('table', id = 'ObjectiveIssue')
  print(financials)
  finTable = pd.read_html(StringIO(str(financials)),header = 0)[0]
  objTable = pd.read_html(StringIO(str(objectives)), header = 0)[0]
  
  info = {}
  info['Refund Date'] = pgsoup.find('td',attrs={'data-title':'Refund Dt'}).string.replace('th','').replace('nd','')
  info['Allotment Date'] = pgsoup.find('td', attrs={'data-title':'Allotment Dt'}).string.replace('th','').replace('nd','')
  info['Listing Date'] = pgsoup.find('td', attrs={'data-title':'Listing Dt'}).string.replace('th','').replace('nd','')
  info['Lot size'] = pgsoup.find('td', attrs={"data-title" : "Market Lot"}).get_text()
  try:
    info['Subscribed (in Retail category)'] = pgsoup.find('td', attrs={'data-title':'RII Offered'}).find_parent('table').find('tbody').find_all('tr')[-1].find('td',attrs={'data-title':re.compile(r'RII-Day\d')}).string
  except:
    info['Subscribed (in Retail category)'] = '0.0x'

  infodf = pd.DataFrame(pd.Series(info))
  infodf.reset_index(level= None, inplace = True, drop = False)
  about = list(pgsoup.find('a',attrs={'title':(company + ' Website')}).find_parent('table').parent.previous_siblings)
  about.reverse()
  about.pop(0)
  about.pop(-1)
  about.pop(-1)
  moreInfo[company] = {"fin": finTable,'obj':objTable,'dates': infodf, 'about':about}

ipoTable['Open'] = ipoTable['Open'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
ipoTable['Close'] = ipoTable['Close'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))

del ipoTable['link']
totalIpo = len(ipoTable)
ipoTable = ipoTable.to_dict(orient='split')

"""
variables used in template:
1. ipotable = ipoTable.to_dict(orient='split') where ipoTable has no links
2. moreInfo as it is
3. activeIPO = len(ipoTable)
4. today = dtetime.now().date()
"""

#convert all to formatted html string and merge with whole template

rawHTML = """
  <!DOCTYPE html>
  <html lang="en">
  <head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Project Status Report</title>
  </head>
  <body style="margin: 0; padding: 0; width: 100% !important; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #F7F8FA; font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color: #2F3542;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%">
  <tr>
  <td align="center" style="padding: 20px 0;">
  <table border="0" cellpadding="0" cellspacing="0" width="900" class="wrapper" style="max-width: 900px; margin: 0 auto;">
  <tr>
  <td align="center" style="padding: 0 10px;">
  <div class="header" style="padding: 50px 20px; text-align: center;">
  <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #2F3542;">Active IPO Report</h1>
  <p style="margin: 10px 0 0; font-size: 16px; color: #57606F; line-height: 1.6;">As of {{today.strftime("%d-%m-%Y")}}, total {{activeIPO}} IPOs are live.</p>
  </div>

  <!-- Main IPO Table inside its own Card -->
  <table border="0" cellpadding="0" cellspacing="0" width="100%">
  <tr>
  <td class="main-table-card" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 10px 40px rgba(47, 53, 66, 0.08);">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" class="report-container" style="border: 1px solid #EAEBEF; border-radius: 8px; overflow: hidden;">
  <thead>
  <tr style="background-color: #F7F8FA;">
  <th align="left" style="font-size: 13px; font-weight: 600; color: #8395A7; text-align: left; padding: 12px 15px; border-bottom: 1px solid #EAEBEF; text-transform: uppercase; letter-spacing: 0.5px;">{{ipotable['columns'][0]}}</th>
  <th align="left" style="font-size: 13px; font-weight: 600; color: #8395A7; text-align: left; padding: 12px 15px; border-bottom: 1px solid #EAEBEF; text-transform: uppercase; letter-spacing: 0.5px;">{{ipotable['columns'][1]}}</th>
  <th align="left" style="font-size: 13px; font-weight: 600; color: #8395A7; text-align: left; padding: 12px 15px; border-bottom: 1px solid #EAEBEF; text-transform: uppercase; letter-spacing: 0.5px;">{{ipotable['columns'][2]}}</th>
  <th align="left" style="font-size: 13px; font-weight: 600; color: #8395A7; text-align: left; padding: 12px 15px; border-bottom: 1px solid #EAEBEF; text-transform: uppercase; letter-spacing: 0.5px;">{{ipotable['columns'][3]}}</th>
  <th align="left" style="font-size: 13px; font-weight: 600; color: #8395A7; text-align: left; padding: 12px 15px; border-bottom: 1px solid #EAEBEF; text-transform: uppercase; letter-spacing: 0.5px;">{{ipotable['columns'][4]}}</th>
  <th align="left" style="font-size: 13px; font-weight: 600; color: #8395A7; text-align: left; padding: 12px 15px; border-bottom: 1px solid #EAEBEF; text-transform: uppercase; letter-spacing: 0.5px;">{{ipotable['columns'][5]}}</th>
  <th align="right" style="font-size: 13px; font-weight: 600; color: #8395A7; text-align: right; padding: 12px 15px; border-bottom: 1px solid #EAEBEF; text-transform: uppercase; letter-spacing: 0.5px;">{{ipotable['columns'][6]}}</th>
  </tr>
  </thead>
  <tbody>
  {% for row in ipotable['data'] %}
  <tr>
  <td style="padding: 12px 15px; border-bottom: 1px solid #F0F2F5; vertical-align: top; color: #2F3542; font-size: 15px; font-weight: 600;">{{ row[0] }}</td>
  <td style="padding: 12px 15px; border-bottom: 1px solid #F0F2F5; vertical-align: top; color: #57606F; font-size: 14px;">{{ row[1] }}</td>
  <td style="padding: 12px 15px; border-bottom: 1px solid #F0F2F5; vertical-align: top; color: #57606F; font-size: 14px;">{{ row[2] }}</td>
  <td style="padding: 12px 15px; border-bottom: 1px solid #F0F2F5; vertical-align: top; color: #57606F; font-size: 14px;">{{ row[3] }}</td>
  <td style="padding: 12px 15px; border-bottom: 1px solid #F0F2F5; vertical-align: top; color: #57606F; font-size: 14px;">{{ row[4] }}</td>
  <td style="padding: 12px 15px; border-bottom: 1px solid #F0F2F5; vertical-align: top; color: #57606F; font-size: 14px;">{{ row[5] }}</td>
  <td align="right" style="padding: 12px 15px; border-bottom: 1px solid #F0F2F5; vertical-align: top; color: #57606F; font-size: 14px;">{{ row[6] }}</td>
  </tr>
  {% endfor %}
  </tbody>
  </table>
  </td>
  </tr>
  </table>

  <!-- Spacer -->
  <table border="0" cellpadding="0" cellspacing="0" width="100%"><tr><td height="30" style="font-size: 30px; line-height: 30px;">&nbsp;</td></tr></table>

  <!-- Company Information Cards -->
  {% for row in ipotable['data'] %}
  <table border="0" cellpadding="0" cellspacing="0" width="100%" class="company-card-container">
  <tr>
  <td>
  <div class="company-card" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 10px 40px rgba(47, 53, 66, 0.08); padding: 30px; margin-bottom: 25px; border: 1px solid #EAEBEF;">
  <h3 style="margin-top: 0; margin-bottom: 25px; color: #2F3542; font-size: 20px; font-weight: 700;">About {{row[0]}}</h3>
  <table border="0" cellpadding="0" cellspacing="0" width="100%">
  <!-- About and Key Information Section -->
  <tr>
  <td width="55%" valign="top" class="details-description" style="font-size: 14px; line-height: 1.7; color: #57606F; padding-right: 25px;">
  {% for p in moreInfo[row[0]]['about'] %}
  <p style="margin-top:0; margin-bottom: 1em;">{{ p }}</p>
  {% endfor %}
  </td>
  <td width="45%" valign="top" style="padding-left: 15px;">
  <div class="data-card" style="background-color: #F7F8FA; border-radius: 8px; padding: 20px; border: 1px solid #EAEBEF;">
  <h4 style="margin-top:0; margin-bottom: 15px; color: #2F3542;">Key Information</h4>
  <table cellpadding="0" cellspacing="0" border="0" class="nested-table" width="100%">
  <tbody>
  {% for r in moreInfo[row[0]]['dates'].to_dict(orient = 'split')['data'] %}
  <tr>
  <td class="key" style="color: #57606F; padding: 10px 4px; border-bottom: 1px solid #EAEBEF; font-size: 14px;">{{r[0]}}</td>
  <td class="value" style="color: #2F3542; font-weight: 600; text-align: right; padding: 10px 4px; border-bottom: 1px solid #EAEBEF; font-size: 14px;">{{r[1]}}</td>
  </tr>
  {% endfor %}
  </tbody>
  </table>
  </div>
  </td>
  </tr>
  <!-- Financial Details Section -->
  <tr>
  <td colspan="2" style="padding-top: 30px;">
  <h4 style="margin-top: 0; margin-bottom: 15px; color: #2F3542;">Financial Details</h4>
  <table cellpadding="0" cellspacing="0" border="0" class="nested-table" width="100%" style="border: 1px solid #EAEBEF; border-radius: 8px; overflow: hidden;">
  <thead>
  <tr style="background-color: #F7F8FA;">
  {% for col_name in moreInfo[row[0]]['fin'].to_dict(orient = 'split')['columns'] %}
  <th style="font-size: 13px; font-weight: 600; color: #8395A7; text-align: left; padding: 12px 15px; border-bottom: 1px solid #EAEBEF;">{{ col_name }}</th>
  {% endfor %}
  </tr>
  </thead>
  <tbody>
  {% for fin_row in moreInfo[row[0]]['fin'].to_dict(orient = 'split')['data'] %}
  <tr>
  {% for data in fin_row %}
  <td style="padding: 12px 15px; border-bottom: 1px solid #F0F2F5; vertical-align: top; color: #57606F; font-size: 14px;">{{ data }}</td>
  {% endfor %}
  </tr>
  {% endfor %}
  </tbody>
  </table>
  </td>
  </tr>
  <!-- Objectives Section -->
  <tr>
  <td colspan="2" style="padding-top: 30px;">
  <h4 style="margin-top: 0; margin-bottom: 15px; color: #2F3542;">Objectives of IPO</h4>
  <table cellpadding="0" cellspacing="0" border="0" class="nested-table" width="100%" style="border: 1px solid #EAEBEF; border-radius: 8px; overflow: hidden;">
  <thead>
  <tr style="background-color: #F7F8FA;">
  {% for col_name in moreInfo[row[0]]['obj'].to_dict(orient = 'split')['columns'] %}
  <th style="font-size: 13px; font-weight: 600; color: #8395A7; text-align: left; padding: 12px 15px; border-bottom: 1px solid #EAEBEF;">{{ col_name }}</th>
  {% endfor %}
  </tr>
  </thead>
  <tbody>
  {% for obj_row in moreInfo[row[0]]['obj'].to_dict(orient = 'split')['data'] %}
  <tr>
  {% for data in obj_row %}
  <td style="padding: 12px 15px; border-bottom: 1px solid #F0F2F5; vertical-align: top; color: #57606F; font-size: 14px;">{{ data }}</td>
  {% endfor %}
  </tr>
  {% endfor %}
  </tbody>
  </table>
  </td>
  </tr>
  </table>
  </div>
  </td>
  </tr>
  </table>
  {% endfor %}

  <div class="footer" style="padding: 40px; text-align: center; font-size: 12px; color: #8395A7;">
  <p>This is an automated report. Do not reply to this email.</p>
  </div>
  </td>
  </tr>
  </table>
  </td>
  </tr>
  </table>
  </body>
  </html>
"""
template = Template(rawHTML)

finalHTML = template.render(today=today,ipotable=ipoTable,moreInfo = moreInfo, activeIPO = totalIpo)

#send mails
if totalIpo:
  for email in recievers['emails']:
    RECEIVER_EMAIL = email
    send_email(finalHTML,totalIpo)
else:
  print("No IPOs are Live")
