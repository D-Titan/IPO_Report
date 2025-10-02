#Update Report without info cards
import requests
import json
import pandas as pd
from bs4 import BeautifulSoup as bs
from datetime import datetime, timedelta

import os

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from io import StringIO
from jinja2 import Template


# Setup mailing details
sender = json.loads(os.environ.get('SENDER'))
receivers = os.environ.get('RECEIVERS') #json.loads(os.environ.get('RECEIVERS'))
urls = json.loads(os.environ.get('URLS'))
url = urls['domain']
reportApi = urls['reportApi']
updateurl = urls['updateurl'] 


SENDER_EMAIL = sender['email']
SENDER_PASSWORD =sender['pass']
RECEIVER_EMAIL = [receivers]
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
              message["From"] = SENDER_EMAIL
              message["To"] = email

              # Attach the HTML body to the message
              part = MIMEText(template.format(email=email), "html")
              message.attach(part)

              server.sendmail(SENDER_EMAIL, email, message.as_string())
              i+=1

            print(f"{i} email{'s' if i>0 else ''} sent successfully!")

    except smtplib.SMTPAuthenticationError:
        print("\nAUTHENTICATION FAILED")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

today = datetime.now()
time = (today + timedelta(hours = 5, minutes = 30)).time()
date = today.date()

print("time: ", time, " Date: ",date)

fy = ''
if date > datetime.strptime(f'31-03-{date.year}', '%d-%m-%Y').date() :
  fy = f'{date.year}-{str(date.year+1)[2:]}'
else:
  fy = f'{date.year -1}-{str(date.year)[2:]}'

# Fetching information from API
ipo = reportApi.format(reportCode = 394, month = date.month, year = date.year, fy = fy)
gmp = reportApi.format(reportCode = 331, month = date.month, year = date.year, fy = fy)
sub = reportApi.format(reportCode = 333, month = date.month, year = date.year, fy = fy)

# Selecting and Renaming Columns
Ipo = pd.DataFrame(json.loads(requests.get(ipo).content)['reportTableData'])
Gmp = pd.DataFrame(json.loads(requests.get(gmp).content)['reportTableData'])
Sub = pd.DataFrame(json.loads(requests.get(sub).content)['reportTableData'])

ipoCols = ["IPO", "IPO Size",   "P/E",  "IPO Price",    "Lot",  "~id", "~Srt_Open", "~Srt_Close",   "~Srt_BoA_Dt",  "~Str_Listing", "~URLRewrite_Folder_Name"]
gmpCols = ["Sub",   "~id",  "Updated-On",   "~urlrewrite_folder_name",  "~gmp_percent_calc"]
subCols = ["Total", "QIB",  "SHNI", "BHNI", "NII",  "RII",  "~id",  "~URLRewrite_Folder_Name"]

ipoColsRenamed = {"IPO":"Issuer Company","IPO Size": "IPO Size","P/E":'PE',"~id": 'id', "~Srt_Open": "Open", "~Srt_Close": "Close", "~Srt_BoA_Dt": "BoA", "~Str_Listing": "Listing",  "~URLRewrite_Folder_Name": "link"}
gmpColsRenamed = {"~id": 'id', "~urlrewrite_folder_name":"gmplink", "~gmp_percent_calc":"GMP"}
subColsRenamed = {"~id": 'id',  "~URLRewrite_Folder_Name": "sublink"}

ipoTable = Ipo[ipoCols].rename(columns = ipoColsRenamed)
subTable = Sub[subCols].rename(columns = subColsRenamed)
gmpTable = Gmp[gmpCols].rename(columns = gmpColsRenamed)

# Cleaning and transforming values
ipoTable['IPO Size'] = ipoTable['IPO Size'].apply(lambda x: float(x.replace('&#8377;','').replace(' Cr','').replace(' Shares','')))
ipoTable["Issuer Company"] = ipoTable["Issuer Company"].str.replace(' IPO','')
ipoTable['Open'] = ipoTable['Open'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date())
ipoTable['Close'] = ipoTable['Close'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date())
ipoTable['BoA'] = ipoTable['BoA'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date())
ipoTable['Listing'] = ipoTable['Listing'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date())

gmpTable['GMP'] = gmpTable['GMP'].apply(lambda x: float(str(x if x != '' else '0')))
subTable['Total'] = subTable['Total'].apply(lambda x: bs(x,'html.parser').find('b').get_text())
subTable['Subscribed'] = subTable['Total'] + subTable['RII'].apply(lambda x: f' (RII: {x})')

# Filtering to Active and Upcoming
upcoming = ipoTable[ipoTable['Open'] > date]
ipoTable = ipoTable[(ipoTable['Open'] <= date) & (ipoTable['Close'] >= date)] #Most Imp change from 'and' to using '&'

# Merging tables 
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


# Converting Dates to string for better representation
ipoTable['Open'] = ipoTable['Open'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
ipoTable['Close'] = ipoTable['Close'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
ipoTable['BoA'] = ipoTable['BoA'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))
ipoTable['Listing'] = ipoTable['Listing'].apply(lambda x: datetime.strftime(x,"%d-%m-%Y"))


#Prepare a dictionary to hold more detailed information for each company moreInfo{company : {}}
moreInfo = {}
refund = []

for index,row in ipoTable.iterrows():
  link  = url + row['link']
  # Loading the ipo page
  pgsoup = bs(requests.get(link).content,'html.parser')
  refund.append(datetime.strftime(datetime.strptime(pgsoup.find('td',attrs={'data-title':'Refund Dt'}).string.replace('th','').replace('nd','').replace('rd','').replace('st',''), '%d %b %Y').date(), '%d-%m-%Y'))


#preparing tables for template
ipoTable['Refund'] = refund
ipoTable = ipoTable.drop(columns=['link', 'Listing', 'id', 'PE','Lot','RII','BoA'])
ipoTable = ipoTable[['Issuer Company', 'Open', 'Close', 'Refund', 'IPO Size', 'IPO Price', 'GMP','Subscribed']]
ipoTable['Subscribed'] = ipoTable['Subscribed'].fillna('0.0')
ipotable = ipoTable.to_dict(orient='split')

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

availIPO = """
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>
    Active IPO Report
    </title>
  </head>
  <body style="margin: 0; padding: 0; width: 100% !important; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #F7F8FA; font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color: #2F3542;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
    <tr>
    <td align="center" style="padding: 20px 0;">
    <table border="0" cellpadding="0" cellspacing="0" class="wrapper" style="max-width: 900px; margin: 0 auto;" width="900">
        <tr>
        <td align="center" style="padding: 0 10px;">
          <div class="header" style="padding: 50px 20px; text-align: center;">
          <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #2c3e50;">
          Active IPO Report
          </h1>
          <p style="margin: 10px 0 0; font-size: 16px; color: #57606F; line-height: 1.6;">
          As of {{date.strftime("%d-%m-%Y")}} {{time.strftime("%H:%M:%S")}}, total {{activeIPO}} IPOs are live.
          </p>
          </div>
          <!-- Main IPO Table inside its own Card -->
          <table border="0" cellpadding="0" cellspacing="0" width="100%">
          <tr>
          <td class="main-table-card" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 10px 40px rgba(47, 53, 66, 0.08);">
          <table border="0" cellpadding="0" cellspacing="0" class="report-container" style="border: 1px solid #EAEBEF; border-radius: 10px; overflow: hidden;" width="100%">
              <thead>
              <tr>
                {% for data in ipotable['columns'] %}
                <th align="left" style="font-size: 16px; text-align: left; padding: 12px 15px; text-transform: uppercase; letter-spacing: 0.5px; background-color: #34495e; color: #ffffff; font-weight: 600; border: none;">
                {{data}}
                </th>
                {% endfor %}
              </tr>
              </thead>
              <tbody>
              {% for row in ipotable['data'] %}
              <tr>
                <td style="padding: 12px 15px; vertical-align: top; font-size: 16px; font-weight:600; border-bottom: 1px solid #f0f0f0; color: #555;">
                {{ row[0] }}
                </td>
                <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                {{ row[1] }}
                </td>
                <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                {{ row[2] }}
                </td>
                <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                {{ row[3] }}
                </td>
                <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                ₹{{ row[4] }} Cr
                </td>
                <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                {{ row[5] }}
                </td>
                <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                {{ row[6] }}%
                </td>
                <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                {{ row[7] }}
                </td>
              </tr>
              {% endfor %}
              </tbody>
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

          <!--- Upcoming Table --->
          <table border="0" cellpadding="0" cellspacing="0" width="100%">
          <div class="header" style="padding: 50px 20px 10px; text-align: center;">
          <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #2c3e50;">
          Upcoming IPOs
          </h1>
          </div>
          <tr>
          <td class="main-table-card" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 10px 40px rgba(47, 53, 66, 0.08);">
          {% if upcominglen != 0 %}
              <table border="0" cellpadding="0" cellspacing="0" class="report-container" style="border: 1px solid #EAEBEF; border-radius: 10px; overflow: hidden;" width="100%">
                <thead>
                <tr>
                    {% for data in upcomingtable['columns'] %}
                    <th align="left" style="font-size: 16px; text-align: left; padding: 12px 15px; text-transform: uppercase; letter-spacing: 0.5px; background-color: #34495e; color: #ffffff; font-weight: 600; border: none;">
                    {{data}}
                    </th>
                    {% endfor %}
                </tr>
                </thead>
                <tbody>
                {% for row in upcomingtable['data'] %}
                <tr>
                    <td style="padding: 12px 15px; vertical-align: top; font-size: 16px; font-weight:600; border-bottom: 1px solid #f0f0f0; color: #555;">
                    {{ row[0] }}
                    </td>
                    <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                    {{ row[1] }}
                    </td>
                    <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                    {{ row[2] }}
                    </td>
                    <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                    {{ row[3] }}
                    </td>
                    <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                    ₹{{ row[4] }} Cr
                    </td>
                    <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                    {{ row[5] }}
                    </td>
                    <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                    {{ row[6] }}%
                    </td>
                    <td style="padding: 15px 12px; vertical-align: top; font-size: 16px; border-bottom: 1px solid #f0f0f0; color: #555; white-space: nowrap;">
                    {{ row[7] }}
                    </td>
                </tr>
                {% endfor %}
                </tbody>
              </table>
          {% else %}
          <tr>
              <td class="details-description" style="font-size: 16px; line-height: 1.7; color: #57606F; text-align: center; padding-right: 25px;" valign="top" width="100">
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
                    <td align="center" style="border-radius: 6px; background-color: #34495e;">
                      <a href="{{updateurl}}" target="_blank" style="display: inline-block; padding: 14px 28px; font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 6px; background-color: #34495e;">
                        Request Updated IPO Information
                      </a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>

          <!--- Footer --->
          <div class="footer" style="padding: 40px; text-align: center; font-size: 14px; color: #8395A7;">
          <p>
          This is an automated report. Do not reply to this email.
          </p>
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

noIPO = """
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>IPO Status Report</title>
  </head>
  <body style="margin: 0; padding: 0; width: 100% !important; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #F7F8FA; font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; color: #2F3542;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td align="center" style="padding: 20px 0;">
          <table border="0" cellpadding="0" cellspacing="0" class="wrapper" style="max-width: 900px; margin: 0 auto;" width="900">
            <tr>
              <td align="center" style="padding: 0 10px;">
                <!-- Header Section -->
                <div class="header" style="padding: 50px 20px; text-align: center;">
                  <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #2c3e50;">
                    IPO Status Report
                  </h1>
                  <p style="margin: 10px 0 0; font-size: 16px; color: #57606F; line-height: 1.6;">
                    As of {{date.strftime("%d-%m-%Y")}} {{time.strftime("%H:%M:%S")}}
                  </p>
                </div>

                <!-- Status Card -->
                <table border="0" cellpadding="0" cellspacing="0" width="100%">
                  <tr>
                    <td class="main-table-card" style="background-color: #ffffff; border-radius: 12px; box-shadow: 0 10px 40px rgba(47, 53, 66, 0.08);">
                      <table border="0" cellpadding="0" cellspacing="0" class="report-container" style="border: 1px solid #EAEBEF; border-radius: 10px; overflow: hidden;" width="100%">
                        <thead>
                          <tr>
                            <th align="left" style="font-size: 16px; text-align: left; padding: 12px 15px; text-transform: uppercase; letter-spacing: 0.5px; background-color: #34495e; color: #ffffff; font-weight: 600; border: none;"></th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td style="padding: 40px 15px; vertical-align: top; font-size: 16px; text-align: center; color: #555;">
                              <h3 style="margin: 0 0 20px; color: #2c3e50; font-size: 22px;">
                                No IPOs Currently Active or Upcoming
                              </h3>
                              <p style="margin: 0; color: #7f8c8d; line-height: 1.6;">
                                There are 0 active IPOs trading in the market and 0 upcoming IPOs scheduled for launch.
                              </p>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                </table>

                <!-- Request Updated Info Button -->
                <table border="0" cellpadding="0" cellspacing="0" width="100%">
                  <tr>
                    <td align="center" style="padding: 40px 0 30px;">
                      <table border="0" cellpadding="0" cellspacing="0">
                        <tr>
                          <td align="center" style="border-radius: 6px; background-color: #34495e;">
                            <a href="{{updateurl}}" target="_blank" style="display: inline-block; padding: 14px 28px; font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 6px; background-color: #34495e;">
                              Request Updated IPO Information
                            </a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <!-- Footer -->
                <div class="footer" style="padding: 40px; text-align: center; font-size: 14px; color: #8395A7;">
                  <p>
                    This is an automated report. Do not reply to this email.
                  </p>
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

if (len(upcoming) + len(upcoming)):
  template = Template(availIPO)
  finalHTML = template.render(date = date, time = time, ipotable = ipotable, moreInfo = moreInfo, activeIPO = totalIpo, upcomingtable = upcomingtable, upcominglen = len(upcoming), updateurl = updateurl)
  send_email(finalHTML,title)

else:
  template = Template(noIPO)
  finalHTML = template.render(date= date, time = time, updateurl = updateurl)
  send_email(finalHTML,"No Active or Upcoming IPOs")
