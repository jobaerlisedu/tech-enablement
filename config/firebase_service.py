import os
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore, auth, storage
from datetime import datetime

# Build paths inside the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')

# Initialize Admin SDK if not already done
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
        if not os.path.isabs(cred_path):
            cred_path = os.path.join(BASE_DIR, cred_path)
            
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
        'storageBucket': bucket_name
    })

db = firestore.client()

bucket = None
if bucket_name:
    try:
        bucket = storage.bucket()
    except Exception as e:
        print(f"Error accessing Firebase Storage bucket: {e}")

def sign_in_with_email_and_password(email, password):
    """
    Authenticate a user with Firebase Auth REST API using email and password.
    Returns the token response dictionary on success, or raises an Exception on failure.
    """
    api_key = os.getenv('FIREBASE_API_KEY')
    if not api_key:
        raise Exception("FIREBASE_API_KEY environment variable is not set.")
    
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        error_info = response.json().get('error', {})
        error_message = error_info.get('message', 'Authentication failed')
        raise Exception(error_message)

def log_audit(user_email, action, details, request=None):
    """
    Create a new system audit log entry in the Firestore database.
    """
    ip = '0.0.0.0'
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
            
    log_entry = {
        'user_email': user_email or 'Anonymous',
        'action': action,
        'details': details,
        'timestamp': datetime.utcnow(),
        'ip': ip
    }
    try:
        db.collection('audit_logs').add(log_entry)
    except Exception as e:
        print(f"Failed to write audit log: {e}")
