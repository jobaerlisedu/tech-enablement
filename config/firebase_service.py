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

def get_unsplash_image(title, category_slug=None):
    """
    Deterministically retrieve a topic-relevant high-resolution Unsplash image url
    based on keywords found in the title or category slug.
    """
    title_lower = title.lower() if title else ""
    cat_lower = category_slug.lower() if category_slug else ""
    
    # Curated high-quality, topic-relevant Unsplash images
    cyber_images = [
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?auto=format&fit=crop&w=800&q=80"
    ]
    cloud_images = [
        "https://images.unsplash.com/photo-1600132806370-bf17e65e942f?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1597839219216-a773cb2473e4?auto=format&fit=crop&w=800&q=80"
    ]
    ai_images = [
        "https://images.unsplash.com/photo-1527474305487-b87b222841cc?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1501426026826-31c667bdf23d?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80"
    ]
    web_images = [
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?auto=format&fit=crop&w=800&q=80"
    ]
    generic_images = [
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1531403009284-440f080d1e12?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=800&q=80"
    ]
    
    # Classify based on title and category
    if any(k in title_lower or k in cat_lower for k in ['security', 'cyber', 'hack', 'lock', 'protect', 'defense']):
        img_list = cyber_images
    elif any(k in title_lower or k in cat_lower for k in ['cloud', 'devops', 'docker', 'kubernetes', 'aws', 'server', 'network']):
        img_list = cloud_images
    elif any(k in title_lower or k in cat_lower for k in ['ai', 'intelligence', 'robot', 'ml', 'machine', 'learning', 'neural']):
        img_list = ai_images
    elif any(k in title_lower or k in cat_lower for k in ['web', 'html', 'css', 'javascript', 'django', 'react', 'program', 'code', 'develop']):
        img_list = web_images
    else:
        img_list = generic_images
        
    # Use deterministic index based on title
    import hashlib
    idx = int(hashlib.md5(title_lower.encode('utf-8')).hexdigest(), 16) % len(img_list)
    return img_list[idx]
