import os
from google.cloud import firestore
from google.oauth2 import service_account

# Write service account JSON from environment variable to a file (for Render)
service_account_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if service_account_json:
    with open("/tmp/firebase-adminsdk.json", "w") as f:
        f.write(service_account_json)
    service_account_path = "/tmp/firebase-adminsdk.json"
else:
    service_account_path = "config/smartchatai-firebase-adminsdk.json"  # fallback for local dev

cred = service_account.Credentials.from_service_account_file(service_account_path)
db = firestore.Client(credentials=cred)