import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

import dotenv
dotenv.load_dotenv()

# Initialize the Firebase Admin SDK from env credentials (same approach as clear_database.py)
if not firebase_admin._apps:
    cred = None

    cred_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
    if cred_json:
        try:
            cred = credentials.Certificate(json.loads(cred_json))
        except Exception as e:
            print(f"Error parsing FIREBASE_CREDENTIALS_JSON: {e}")

    if not cred:
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            raise FileNotFoundError(
                f"Firebase credentials not found. Please provide credentials via the "
                f"FIREBASE_CREDENTIALS_JSON environment variable, or place your service account "
                f"JSON file at '{cred_path}'."
            )

    firebase_admin.initialize_app(cred, {
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
    })

db = firestore.client()

# Intended initial superadmin account. CHANGE THESE to your preferred values.
ADMIN_EMAIL = 'admin@tech-enablement.info'
ADMIN_PASSWORD = 'TU&heSwat5'
ADMIN_DISPLAY_NAME = 'System Admin'
ADMIN_ROLE = 'Superadmin'
ADMIN_STATUS = 'active'


def ensure_superuser(client=None):
    """
    Idempotent bootstrap: create the superadmin ONLY if no user exists in the
    'users' collection. If any user already exists (including a superadmin),
    skip creation. This guards against duplicates on repeat runs/deploys.
    """
    client = client or db

    # Guard: if there is at least one existing user, never override it.
    if len(list(client.collection('users').list_documents())) > 0:
        print("Existing user(s) found in 'users' collection - skipping superadmin creation.")
        return False

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    try:
        django.setup()
    except Exception as e:
        print(f"Failed to initialize Django (for password hashing): {e}")
        return False

    from django.contrib.auth.hashers import make_password
    user_profile = {
        "uid": "system-admin-uid",
        "email": ADMIN_EMAIL,
        "display_name": ADMIN_DISPLAY_NAME,
        "role": ADMIN_ROLE,
        "status": ADMIN_STATUS,
        "password": make_password(ADMIN_PASSWORD)
    }
    client.collection('users').document(user_profile["uid"]).set(user_profile)
    print(f"Superadmin created: {ADMIN_EMAIL}")
    return True


if __name__ == '__main__':
    ensure_superuser(db)