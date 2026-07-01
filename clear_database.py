import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Set up environment variables
import dotenv
dotenv.load_dotenv()

# Initialize Admin SDK
if not firebase_admin._apps:
    cred = None
    
    # 1. Try loading credentials from the environment variable (raw JSON string)
    cred_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
    if cred_json:
        try:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            print("Firebase Admin SDK initialized using FIREBASE_CREDENTIALS_JSON environment variable.")
        except Exception as e:
            print(f"Error parsing FIREBASE_CREDENTIALS_JSON: {e}")
            
    # 2. Try loading from the file path if not loaded via env variable
    if not cred:
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            print(f"Firebase Admin SDK initialized using certificate file at: {cred_path}")
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

def clear_database():
    print("Purging all test and dummy data from Firestore...")
    collections = ['categories', 'authors', 'blogs', 'courses', 'tutorials', 'users', 'audit_logs']
    
    for col_name in collections:
        col_ref = db.collection(col_name)
        docs = col_ref.list_documents()
        deleted = 0
        for doc in docs:
            doc.delete()
            deleted += 1
        print(f"Cleared {deleted} documents from '{col_name}' collection.")

    # Re-seed the default Superadmin user profile so they can immediately log in
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    try:
        django.setup()
        from django.contrib.auth.hashers import make_password
        default_admin_uid = "system-admin-uid"
        user_profile = {
            "uid": default_admin_uid,
            "email": "admin@techenablement.com",
            "display_name": "System Admin",
            "role": "Superadmin",
            "status": "active",
            "password": make_password("AdminPassword123!")
        }
        db.collection('users').document(default_admin_uid).set(user_profile)
        print("Default System Admin user profile seeded successfully.")
    except Exception as e:
        print(f"Failed to seed default admin user: {e}")

    print("Firestore database is now completely clean and ready for production use!")

if __name__ == '__main__':
    clear_database()
