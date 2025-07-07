from google.cloud import firestore
from google.oauth2 import service_account

cred = service_account.Credentials.from_service_account_file("config/smartchatai-firebase-adminsdk.json")
db = firestore.Client(credentials=cred)