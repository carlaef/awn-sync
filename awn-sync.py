from requests_oauthlib import OAuth2Session
import requests
import json
import os
import dotenv

dotenv.load_dotenv()

DONORBOX_USERNAME = os.environ.get('DONORBOX_USERNAME')
DONORBOX_API_KEY = os.environ.get('DONORBOX_API_KEY')
DONORBOX_AUTH = (DONORBOX_USERNAME, DONORBOX_API_KEY)
DONORBOX_BASE_URL = 'https://donorbox.org/api/v1/'

ZOHO_CLIENT_ID = os.environ.get('ZOHO_CLIENT_ID')
ZOHO_CLIENT_SECRET = os.environ.get('ZOHO_CLIENT_SECRET')
ZOHO_BASE_URL = 'https://www.zohoapis.com/crm/v2/Contacts'

oauth = OAuth2Session(ZOHO_CLIENT_ID, redirect_uri='https://carlaef.org/', scope=('ZohoCRM.modules.contacts.all',))
authorization_url, state = oauth.authorization_url('https://accounts.zoho.com/oauth/v2/auth', access_type='offline')
print('Please visit', authorization_url)
auth_response = input('Enter url: ')
token = oauth.fetch_token('https://accounts.zoho.com/oauth/v2/token',
        authorization_response=auth_response, client_secret=ZOHO_CLIENT_SECRET)

current_crm_members = {}
current_donorbox_members = {}

print("Locating current members...")
page = 1
while True:
    resp = oauth.get(ZOHO_BASE_URL + '?cvid=2914993000001009005&converted=both&page=%d&fields=Email,Monthly_Subscription'%(page))
    if resp.status_code != 200:
        break
    for contact in resp.json()['data']:
        if contact['Monthly_Subscription'] is not None:
            current_crm_members[contact['Email']] = contact
    print(page * 200, 'rows')
    page += 1

print("Found %d members in Zoho"%(len(current_crm_members)))
page = 1
while True:
    donations = requests.get(DONORBOX_BASE_URL + 'donations?page=%d'%(page), auth=DONORBOX_AUTH).json()

    if len(donations) == 0:
        break

    for donation in donations:
        if donation['recurring'] and donation['first_recurring_donation']:
            donorEmail = donation['donor']['email']
            amount = float(donation['amount'])
            donorContact = {
                'Last_Name': donation['donor']['last_name'],
                'First_Name': donation['donor']['first_name'],
                'Email': donorEmail,
                'Monthly_Subscription': amount,
                'Membership_Basis': 'Monthly',
                'Start': donation['donation_date']
            }
            current_donorbox_members[donorEmail] = donorContact

    page += 1

print("Found %d members in donorbox."%(len(current_donorbox_members)))
updated_contacts = []

for existingContact in current_crm_members:
    if existingContact not in current_donorbox_members:
        print("De-membering", existingContact)
        updated_contacts.append({
            'Email': existingContact,
            'Monthly_Subscription': None,
            'Membership_Basis': 'Not a member',
            'Start': None
        })

for email, currentContact in current_donorbox_members.items():
    if email in current_crm_members and current_crm_members[email]['Monthly_Subscription'] == currentContact['Monthly_Subscription']:
        print("Already in sync:", email)
        continue
    print("Updating", email)
    updated_contacts.append(currentContact)

data = {'data': updated_contacts}
print("Updating", len(updated_contacts), 'contacts')
if len(updated_contacts) >= 0:
    response = oauth.post(ZOHO_BASE_URL+'/upsert', data=json.dumps(data))
    if response.status_code != 200:
        raise Exception(response.text)
