import requests
import json
import pandas as pd
from bs4 import BeautifulSoup as bs
from datetime import datetime, timedelta

from google import genai
from google.genai import types

import os

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from io import StringIO
from jinja2 import Template


# Fetching variables from environment
sender = json.loads(os.environ.get('SENDER'))
urls = json.loads(os.environ.get('URLS'))
apiKey = json.loads(os.environ.get('GEMINI_API_KEY'))['api_key']
brevoapi = json.loads(os.environ.get('BREVO_API'))['api_key']
cache = json.loads(os.environ.get('cache'))

cacheAPI = cache['cacheAPI']
cacheURL = cache['cacheURL']

url = urls['domain']
reportApi = urls['reportApi']
updateurl = urls['updateurl'] 

brevo = "https://api.brevo.com/v3/contacts"

headers = {
    'api-key':brevoapi,
    'accept':'application/json'
}

offset = 0
count = 500
params = {
    'listIds':4,
    'limit':500,
    'offset': offset
}

subs = []
while count == 500 :
  res = requests.get(brevo,headers = headers, params = params).content
  response = json.loads(res)
  subs += response.get('contacts', [])
  count = response["count"]
  offset += 500

# Setup mailing details
SENDER_EMAIL = sender['email']
SENDER_PASSWORD = sender['pass']
RECEIVER_EMAIL = subs
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
            for item in RECEIVER_EMAIL:
              if not item["emailBlacklisted"]:
                  email = item['email']
              else:
                  continue
                
              # Create the Email Message
              message = MIMEMultipart("alternative")
              message["Subject"] = title
              message["From"] = f'IPO REPORT <{SENDER_EMAIL}>'
              message["To"] = email

              # Attach the HTML body to the message
              part = MIMEText(template.format(email=email), "html")
              message.attach(part)

              # Send email
              server.sendmail(SENDER_EMAIL, email, message.as_string())
              i+=1

            print(f"{i} email{'s' if i>0 else ''} sent successfully!")

    except smtplib.SMTPAuthenticationError:
        print("\nAUTHENTICATION FAILED")

    except Exception as e:
        print(f"\nAn error occurred: {e}")


def summarize(content,api_key):
  client = genai.Client(api_key = api_key)

  config=types.GenerateContentConfig(
          system_instruction="""
    You are an AI tasked with generating a concise HTML summary of a given company description.

    Your response MUST adhere to the following strict rules:
    1.  HTML ONLY: Your entire output must be a single HTML <div> element. Do not include '<html>', '<head>', '<body>' tags, or any other text outside this single '<div>'.
    2.  NO MARKDOWN: Do not use any Markdown formatting (e.g., ###, **text**, * text,  ```html```). All formatting must be done using HTML tags like '<b>', '<strong>', '<p>', and '<i>'.
    3.  CORE FOCUS: The summary must exclusively extract and present (only available ones from) two key pieces of information:
        - What the company does: Its core services, products, or mission.
        - Who its customers are: Its primary consumers, clients, or target market.
        Keep phrasing neutral and factual (no marketing language, no adjectives like “best”, “leading”, or subjective claims). Only present those sections about which the description specifies, otherwise avoid generating that section.
    4.  CONCISE: Keep the text simple and to the point. Avoid jargon and extraneous details.  The entire <div> must be no more than 80 words total.
    5.  STRUCTURE: Use '<p>' tags to separate sections and '<b>' or '<strong>' tags to create bolded titles for each section(e.g., "Core Services:", "Primary Customers:") and '<ol>' for displaying list.

    example of output:
    <div>
      <p><b>text to bold: </b> text1</p>
      <p><b>text to bold: </b> text2</p>
      <p><b>text to bold: </b>
        <ol>
          <li>item</li>
          <li>item1</li>
          <li>item2</li>
        </ol>
      </p>
    </div>

    do not provide ouput as a code snippet
          """,
          thinking_config=types.ThinkingConfig(thinking_budget=0), # Disables thinking
          )
  contents=f"""
    Here is the company description you are to summarize: {content}
  """
  model = "gemini-2.5-flash-lite"

  response = client.models.generate_content(model = model, config = config, contents = contents)
  return response.text


today = datetime.now()
time = (today + timedelta(hours = 5, minutes = 30)).time()
date = today.date()

fy = ''
if date > datetime.strptime(f'31-03-{date.year}', '%d-%m-%Y').date() :
  fy = f'{date.year}-{str(date.year+1)[2:]}'
else:
  fy = f'{date.year -1}-{str(date.year)[2:]}'

#Fetching Data
ipo = reportApi.format(reportCode = 394, month = date.month, year = date.year, fy = fy)
gmp = reportApi.format(reportCode = 331, month = date.month, year = date.year, fy = fy)
sub = reportApi.format(reportCode = 333, month = date.month, year = date.year, fy = fy)

Ipo = pd.DataFrame(json.loads(requests.get(ipo).content)['reportTableData'])
Gmp = pd.DataFrame(json.loads(requests.get(gmp).content)['reportTableData'])
Sub = pd.DataFrame(json.loads(requests.get(sub).content)['reportTableData'])

#Selecting and Renaming columns
ipoCols = ["IPO", "IPO Size",   "P/E",  "IPO Price",    "Lot",  "~id", "~Srt_Open", "~Srt_Close",   "~Srt_BoA_Dt",  "~Str_Listing", "~URLRewrite_Folder_Name"]
gmpCols = ["Sub",   "~id",  "Updated-On",   "~urlrewrite_folder_name",  "~gmp_percent_calc"]
subCols = ["Total", "QIB",  "SHNI", "BHNI", "NII",  "RII",  "~id",  "~URLRewrite_Folder_Name"]

ipoColsRenamed = {"IPO":"Issuer Company","IPO Size": "IPO Size","P/E":'PE',"~id": 'id', "~Srt_Open": "Open", "~Srt_Close": "Close", "~Srt_BoA_Dt": "BoA", "~Str_Listing": "Listing",  "~URLRewrite_Folder_Name": "link"}
gmpColsRenamed = {"~id": 'id', "~urlrewrite_folder_name":"gmplink", "~gmp_percent_calc":"GMP"}
subColsRenamed = {"~id": 'id',  "~URLRewrite_Folder_Name": "sublink"}

ipoTable = Ipo[ipoCols].rename(columns = ipoColsRenamed)
subTable = Sub[subCols].rename(columns = subColsRenamed)
gmpTable = Gmp[gmpCols].rename(columns = gmpColsRenamed)

#Cleaning and converting table values
ipoTable['IPO Size'] = ipoTable['IPO Size'].apply(lambda x: x.replace('&#8377;','').replace(' Cr','').replace(' Shares',''))
ipoTable["Issuer Company"] = ipoTable["Issuer Company"].str.replace(' IPO','')
ipoTable['Open'] = ipoTable['Open'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date())
ipoTable['Close'] = ipoTable['Close'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date())
ipoTable['BoA'] = ipoTable['BoA'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date())
ipoTable['Listing'] = ipoTable['Listing'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date())

gmpTable['GMP'] = gmpTable['GMP'].apply(lambda x: float(str(x if x != '' else '0')))
subTable['Total'] = subTable['Total'].apply(lambda x: bs(x,'html.parser').find('b').get_text())
subTable['RII'] = subTable['RII'].fillna(0.0)
subTable['Subscribed'] = subTable['Total'] + subTable['RII'].apply(lambda x: f' (RII: {x})')


#Filtering tables to keep Active and Upcoming IPOs
upcoming = ipoTable[ipoTable['Open'] > date]
ipoTable = ipoTable[(ipoTable['Open'] <= date) & (ipoTable['Close'] >= date)] #Most Imp change from 'and' to using '&'

# Merging and sorting
ipoTable = ipoTable.merge(gmpTable[['GMP','id']], on = 'id', how='left')
ipoTable = ipoTable.merge(subTable[['Subscribed','id']], on = 'id', how='left')
ipoTable = ipoTable.merge(subTable[['RII','id']], on = 'id', how='left')
ipoTable = ipoTable.sort_values(by=['Close','GMP'], ascending=[True, False])

upcoming = upcoming.merge(gmpTable[['GMP','id']], on = 'id', how='left')
upcoming = upcoming.fillna(0.0)
upcoming = upcoming.sort_values(by=['Close','GMP'], ascending=[True, False])
upcoming['Open'] = upcoming['Open'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
upcoming['Close'] = upcoming['Close'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
upcoming['BoA'] = upcoming['BoA'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))

title2 = "No IPOs are live"
subs=[]
if not subs:
  title2 = "0 subscribers to send report"
  

# Preparing subject for email
closing = len(ipoTable[ipoTable['Close'] == date])
starting = len(ipoTable[ipoTable['Open'] == date])
totalIpo = len(ipoTable)

title = ''

title_parts = []

if closing:
    title_parts.append(f"{closing} IPO{'s' if closing > 1 else ''} closing")
if starting:
    title_parts.append(f"{starting} IPO{'s' if starting > 1 else ''} starting")

if title_parts:
    title = " and ".join(title_parts) + f" today — {totalIpo} IPOs live in total"
else:
    title = f"{totalIpo} IPO{'s' if totalIpo > 1 else ''} are live today"


# Converting dates back to string for better representation
ipoTable['Open'] = ipoTable['Open'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
ipoTable['Close'] = ipoTable['Close'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
ipoTable['BoA'] = ipoTable['BoA'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
ipoTable['Listing'] = ipoTable['Listing'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
ipoTable['RII'] = ipoTable['RII'].fillna(0.0)

# Prepare a dictionary to hold more detailed information for each company moreInfo{company : {}}
moreInfo = {}
refund = []

for index,row in ipoTable.iterrows():
  company = row['Issuer Company']
  link  = url + row['link']

  # Loading the ipo page
  pgsoup = bs(requests.get(link).content,'html.parser')

  # Extracting information
  financials = pgsoup.find('table', id = 'financialTable')
  objectives = pgsoup.find('table', id = 'ObjectiveIssue')

  if financials:
      finTable = pd.read_html(StringIO(str(financials)),header = 0)[0]
      finTable = finTable.fillna('')
      finTable = finTable.iloc[:-1]
  else:
      finTable = pd.DataFrame()

  if objectives:
      objTable = pd.read_html(StringIO(str(objectives)), header = 0)[0]
      objTable = objTable.fillna('')
  else:
      objTable = pd.DataFrame() 

  info = {}
  fresh = pgsoup.find('td', attrs={"data-title" : "Fresh Issue Size"})
  issue = pgsoup.find('td', attrs={'data-title' : 'Issue Size'}).get_text()

  info['PE'] = row['PE']
  info['Subscribed (RII)'] = row['RII'] if row['RII'] else '0.0'

  if fresh:
    info['Fresh Issue Size'] = fresh.get_text()
  else:
    info['Offer For Sale'] =  issue

  info['Lot Size'] = f"{row['Lot']} Shares"
  info['Allotment Date'] = row['BoA']
  info['Refund Date'] = datetime.strftime(datetime.strptime(pgsoup.find('td',attrs={'data-title':'Refund Dt'}).string.replace('th','').replace('nd','').replace('rd','').replace('st',''), '%d %b %Y').date(), '%d-%m-%Y')
  info['Listing Date'] = row['Listing']

  refund.append(info['Refund Date'])

  infodf = pd.DataFrame(pd.Series(info))
  infodf.reset_index(level= None, inplace = True, drop = False)

  about = """ """
  for section in pgsoup.find('a',attrs={'title':(company + ' Website')}).find_parent('table').parent.previous_siblings:
    about = section.get_text() + about
      
  summary = summarize(about,apiKey)

  moreInfo[company] = {"fin": finTable,'obj':objTable,'dates': infodf, 'about':summary}

# Preparing table for template
ipoTable['Refund'] = refund
ipoTable = ipoTable.drop(columns=['link', 'Listing', 'id', 'PE','Lot','RII','BoA'])
ipoTable = ipoTable[['Issuer Company', 'Open', 'Close', 'Refund', 'IPO Size', 'IPO Price', 'GMP','Subscribed']]
ipoTable['Subscribed'] = ipoTable['Subscribed'].fillna('0.0')
ipoTable = ipoTable.to_dict(orient='split')

upcoming = upcoming.drop(columns=['link', 'Listing', 'id','Lot'])
upcoming = upcoming[['Issuer Company', 'Open', 'Close', 'BoA', 'IPO Size', 'IPO Price', 'GMP','PE']]
upcomingtable = upcoming.to_dict(orient='split')

"""
Variables used in template:
1. ipotable = ipoTable.to_dict(orient='split') where ipoTable has no links
2. moreInfo as it is
3. activeIPO = len(ipoTable)
4. date = dtetime.now().date()
5. upcomingtable = upcoming.to_dict(orient='split)
"""

#Render the collected information into an HTML email template.

rawHTML = """
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>
    Active IPO Report
    </title>
  </head>
  <body style="margin: 0; padding: 0; width: 100% !important; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #f4f4f4; font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color: #000000;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
    <tr>
    <td align="center" style="padding: 20px 0;">
    <table border="0" cellpadding="0" cellspacing="0" class="wrapper" style="max-width: 900px; margin: 0 auto;" width="900">
      <tr>
      <td align="center" style="padding: 0 10px;">
        <div class="header" style="padding: 50px 20px; text-align: center;">
        <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #000000;">
        Active IPO Report
        </h1>
        <p style="margin: 10px 0 0; font-size: 16px; color: #333333; line-height: 1.6;">
        As of {{date.strftime("%d-%m-%Y")}} {{time.strftime("%H:%M:%S")}}, total {{activeIPO}} IPOs are live.
        </p>
        </div>
        <!-- Main IPO Table inside its own Card -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
        <td class="main-table-card" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);">
        <table border="0" cellpadding="0" cellspacing="0" class="report-container" style="border: 1px solid #dddddd; border-radius: 10px; overflow: hidden;" width="100%">
         
          {% if activeIPO != 0 %}
          <thead>
          <tr>
            {% for data in ipotable['columns'] %}
            <th align="left" style="font-size: 16px; text-align: left; padding: 12px 15px; text-transform: uppercase; letter-spacing: 0.5px; background-color: #000000; color: #ffffff; font-weight: 600; border: none;">
            {{data}}
            </th>
            {% endfor %}
          </tr>
          </thead>
          <tbody>
          {% for row in ipotable['data'] %}
          <tr>
            <td style="padding: 12px 15px; vertical-align: top; font-size: 16px; font-weight:600; border-bottom: 1px solid #dddddd; color: #555;">
            {{ row[0] }}
            </td>
            <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
            {{ row[1] }}
            </td>
            <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
            {{ row[2] }}
            </td>
            <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
            {{ row[3] }}
            </td>
            <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
            ₹{{ row[4] }} Cr
            </td>
            <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
            {{ row[5] }}
            </td>
            <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
            {{ row[6] }}%
            </td>
            <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
            {{ row[7] }}
            </td>
          </tr>
          {% endfor %}
          </tbody>
        {% else %}
                <thead>
                <th align="left" style="font-size: 16px; text-align: left; padding: 12px 15px; text-transform: uppercase; letter-spacing: 0.5px; background-color: #000000; color: #ffffff; font-weight: 600; border: none;"></th>
        </thead>
        <tbody>
        <tr>
                <td class="details-description" style="font-size: 16px; line-height: 1.7; color: #333333; text-align: center; padding: 25px;">
                        <p>As of {{ date.strftime("%d-%m-%Y") }} {{time.strftime("%H:%M:%S")}}, no IPOs are live.</p>
                </td>
        </tr>
        </tbody>
        {% endif %}
        </table>
        </td>
        </tr>
        </table>
        <!-- Spacer -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
        <td height="30" style="font-size: 30px; line-height: 30px;">
        </td>
        </tr>
        </table>
        
        <!-- Company Information Cards -->
        {% if activeIPO != 0 %}
        {% for row in ipotable['data'] %}
        <table border="0" cellpadding="0" cellspacing="0" class="company-card-container" width="100%">
        <tr>
        <td>
        <div class="company-card" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08); padding: 30px; margin-bottom: 25px; border: 1px solid #dddddd;">
          <h3 style="margin-top: 0; margin-bottom: 20px; color: #000000; font-size: 24px; font-weight: 700;">
          About {{row[0]}}
          </h3>
          <table border="0" cellpadding="0" cellspacing="0" width="100%">
          <!-- About and Key Information Section -->
          <tr>
            <td class="details-description" style="font-size: 16px; line-height: 1.7; color: #333333; padding-right: 25px;" valign="top" width="55%">
            {{moreInfo[row[0]]['about']}}
            </td>
            <td style="padding-left: 15px;" valign="top" width="45%">
            <div class="data-card" style="background-color: #eeeeee; border-radius: 8px; padding: 20px 20px 0px; border: 2px solid #cccccc;">
            <h3 style="margin-top:0; margin-bottom: 18px; color: #000000; font-size: 18px">
            Key Information
            </h3>
            <table border="0" cellpadding="0" cellspacing="0" class="nested-table" width="100%">
            <tbody>
              {% for r in moreInfo[row[0]]['dates'].to_dict(orient = 'split')['data'] %}
              <tr>
              <td class="key" style="color: #000000; padding: 4px 4px; font-size: 14px;">
                {{r[0]}}
              </td>
              <td class="value" style="color: #000000; font-weight: 600; text-align: right; padding: 4px 4px; font-size: 14px;">
                {{r[1]}}
              </td>
              </tr>
              {% endfor %}
              <div style="padding: 8px 4px"></div>
            </tbody>
            </table>
            </div>
            </td>
          </tr>
          <!-- Financial Details Section -->
          <tr>
            <td colspan="2" style="padding-top: 30px;">
            <h3 style="margin-top: 0; margin-bottom: 18px; color: #000000;font-size:18px">
            Financial Details
            </h3>
            {% if not moreInfo[row[0]]['fin'].empty %}
            <table border="0" cellpadding="0" cellspacing="0" class="nested-table" style="border: 2px solid #cccccc; border-radius: 8px; overflow: hidden;" width="100%">
            <thead>
            <tr style="background-color: #eeeeee">
              {% for col_name in moreInfo[row[0]]['fin'].to_dict(orient = 'split')['columns'] %}
              <th style="font-size: 16px; font-weight: 600; text-align: left; padding: 12px 15px; background-color: #eeeeee; color: #000000; border-bottom: 2px solid #cccccc;">
              {{ col_name }}
              </th>
              {% endfor %}
            </tr>
            </thead>
            <tbody>
            {% for fin_row in moreInfo[row[0]]['fin'].to_dict(orient = 'split')['data'] %}
            <tr>
              {% for data in fin_row %}
              <td style="padding: 12px 15px; border-bottom: 2px solid #eeeeee; vertical-align: top; font-size: 16px;">
              {{ data }}
              </td>
              {% endfor %}
            </tr>
            {% endfor %}
            </tbody>
            </table>
            {% else %}
            <table>
              <tbody>
                <tr>
                  <td></td>
                </tr>
              </tbody>
            </table>
            </td>
          </tr>
          {% endif %}
          <!-- Objectives Section -->
          <tr>
            <td colspan="2" style="padding-top: 30px;">
            <h3 style="margin-top: 0; margin-bottom: 18px; color: #000000; font-size:18px">
            Objectives of IPO
            </h3>
            {% if not moreInfo[row[0]]['obj'].empty %}
            <table border="0" cellpadding="0" cellspacing="0" class="nested-table" style="border: 2px solid #cccccc; border-radius: 8px; overflow: hidden;" width="100%">
            <thead>
            <tr style="background-color: #eeeeee">
              {% for col_name in moreInfo[row[0]]['obj'].to_dict(orient = 'split')['columns'] %}
              <th style="font-size: 16px; font-weight: 600; text-align: left; padding: 12px 15px; background-color: #eeeeee; color: #000000; border-bottom: 2px solid #cccccc;">
              {{ col_name }}
              </th>
              {% endfor %}
            </tr>
            </thead>
            <tbody>
            {% for obj_row in moreInfo[row[0]]['obj'].to_dict(orient = 'split')['data'] %}
            <tr>
              {% for data in obj_row %}
              <td style="padding: 12px 15px; border-bottom: 2px solid #eeeeee; vertical-align: top; font-size: 16px;">
              {{ data }}
              </td>
              {% endfor %}
            </tr>
            {% endfor %}
            </tbody>
            </table>
            {% else %}
            <tr>
            <table>
              <tbody>
                <tr>
                  <td class="details-description" style="font-size: 16px; line-height: 1.7; color: #333333; padding-right: 25px;" valign="top" width="100%">
                  <p>
                  The Company will not receive any proceeds from the Offer. All Offer Proceeds shall be received by the Selling Shareholder subsequent to the deduction of Offer-related expenses and applicable taxes, which shall be the responsibility of the Selling Shareholders.
                  </p>
                  </td>
                </tr>
              </tbody>
            </table>
            </tr>
            {% endif %}
            </td>
          </tr>

          </table>
        </div>
        </td>
        </tr>
        </table>
        {% endfor %}
        {% endif %}

        <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <div class="header" style="padding: 50px 20px 10px; text-align: center;">
        <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #000000;">
        Upcoming IPOs
        </h1>
        </div>
        <tr>
        <td class="main-table-card" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);">
        {% if upcominglen != 0 %}
          <table border="0" cellpadding="0" cellspacing="0" class="report-container" style="border: 1px solid #dddddd; border-radius: 10px; overflow: hidden;" width="100%">
            <thead>
            <tr>
              {% for data in upcomingtable['columns'] %}
              <th align="left" style="font-size: 16px; text-align: left; padding: 12px 15px; text-transform: uppercase; letter-spacing: 0.5px; background-color: #000000; color: #ffffff; font-weight: 600; border: none;">
              {{data}}
              </th>
              {% endfor %}
            </tr>
            </thead>
            <tbody>
            {% for row in upcomingtable['data'] %}
            <tr>
              <td style="padding: 12px 15px; vertical-align: top; font-size: 16px; font-weight:600; border-bottom: 1px solid #dddddd; color: #555;">
              {{ row[0] }}
              </td>
              <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
              {{ row[1] }}
              </td>
              <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
              {{ row[2] }}
              </td>
              <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
              {{ row[3] }}
              </td>
              <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
              ₹{{ row[4] }} Cr
              </td>
              <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
              {{ row[5] }}
              </td>
              <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
              {{ row[6] }}%
              </td>
              <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #dddddd; color: #555; white-space: nowrap;">
              {{ row[7] }}
              </td>
            </tr>
            {% endfor %}
            </tbody>
          </table>
        {% else %}
        <tr>
          <td class="details-description" style="font-size: 16px; line-height: 1.7; color: #333333; text-align: center; padding: 25px;" valign="top" width="100">
            <p>As of {{ date.strftime("%d-%m-%Y") }} {{time.strftime("%H:%M:%S")}}, there are no upcoming IPOs</p>
          </td>
        </tr>
        {% endif %}

        </td>
        </tr>
        </table>

        <!-- Request Updated Info Button -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td align="center" style="padding: 40px 0 30px;">
              <table border="0" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="border-radius: 6px; background-color: #000000;">
                    <a id = "updateBtn" href="{{updateurl}}" target="_blank" style="display: inline-block; padding: 14px 28px; font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 6px; background-color: #000000;">
                      Request Updated IPO Information
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <!-- FOOTER START-->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-top: 20px;">
            <tr>
                <td align="center" style="padding: 0 20px 50px 20px;">
                    <!-- Thick Separator Line -->
                    <div style="height: 4px; width: 100%; background-color: #000000; max-width: 100px; margin-bottom: 30px;"></div>

                    <!-- Navigation Links -->
                    <p style="margin: 0 0 25px 0; font-size: 13px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">
                        <a href="#Disclaimer" style="text-decoration: none; color: #000000; border-bottom: 2px solid #000000; padding-bottom: 2px;">Disclaimer</a>
                        <span style="padding: 0 25px; color: #cccccc;">|</span>
                        <a href="https://f2792238.sibforms.com/serve/MUIFALPKgXs7hLhhjLehz-MYAHTyFvj3mDWIQp8fVMI6mfOIZzJCZIFqYc1iN3wmC93-rqAkVoe-cSxyFkgIxdXPVF6u15Cj1Nwtq5thPBXfTvTj-PpBX4TnUtu305bjt5c0oj4Fd5sVTMDB3fw_2EaaVW2oN-sloWDAT8wdM7-Sj7y_WgIWvVdCp2_jXwTmRioQgsOUkBj3FAiBew==" style="text-decoration: none; color: #000000; border-bottom: 2px solid #000000; padding-bottom: 2px;">Unsubscribe</a>
                    </p>

                    <!-- Disclaimer Text -->
                    <p style="margin: 0 auto 20px auto; font-size: 12px; line-height: 1.8; color: #777777; max-width: 800px; text-align: center;">
                        <strong style="color: #000000;">Disclaimer:</strong> This service provides consolidated information from publicly available sources believed to be reliable, but we do not guarantee its accuracy or completeness. All dates (Refund, Allotment, Listing) are tentative. We do not trade in or advise Gray Market Premium (GMP) trading. The 'About' section is AI-summarized (Gemini-2.5-flash-lite). We are not registered with SEBI as a research analyst or investment advisor. This is not financial advice, an endorsement, or a recommendation. All information is for informational purposes only. Please conduct your own due diligence by referring to the Red Herring Prospectus (RHP), official exchange websites (NSE/BSE), and official websites of respective companies.
                    </p>

                    <!-- Automated Note -->
                    <p style="margin: 0; font-size: 12px; color: #aaaaaa; text-transform: uppercase; letter-spacing: 0.5px;">
                        This is an automated report &mdash; please do not reply.
                    </p>
                </td>
            </tr>
        </table>
        <!--- FOOTER END --->
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
finalHTML = template.render(date = date, time = time, ipotable = ipoTable, moreInfo = moreInfo, activeIPO = totalIpo, upcomingtable = upcomingtable, upcominglen = len(upcoming), updateurl = updateurl)



#Caching this report 
headers = {
    "Authorization": f"Bearer {cacheAPI}",
    "Content-Type": "text/plain"
}
data = finalHTML

cacheResponse = requests.put(cacheURL, headers=headers, data=data)
print(cacheResponse.status_code)

# Finally sending emails
if totalIpo:
  send_email(finalHTML,title)
else:
  print(title2)
