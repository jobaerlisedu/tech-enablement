# Tech Enablement - Django & Firebase CMS

A premium, content-rich Content Management System (CMS) and learning platform built with **Python Django** and **Google Firebase**. The application features a visitor-facing client interface with research blogs and interactive courses, alongside a fully secured administrative CMS dashboard with live previews, media uploads, and user management.

---

## 🚀 Key Features

### 🌐 Visitor Frontend Client
*   **Home Page**: Clean, modern interface displaying the latest research blogs and courses.
*   **Research Blogs (4x5 Grid)**:
    *   24-card grid organized in 4 columns and 5 rows.
    *   Dynamic client-side pagination.
    *   Keyword search filtering by title, summary, content, author, and category.
    *   **Social Sharing Dropdown**: Share blogs directly to Twitter, Facebook, LinkedIn, or Copy Link with clipboard toast notifications.
*   **Courses & Interactive Course Viewer**:
    *   Card listing with "Get Started" buttons.
    *   **Split-Pane Course Reader**:
        *   *Left Sidebar*: Back button, lesson search filtering, and lesson list.
        *   *Right Panel*: Inline `iframe` rendering markdown lesson content and code snippets with syntax highlighting.
        *   *Navigator controls*: Prev / Next buttons to progress through lessons asynchronously.

### 🛡️ CMS Backend Control Panel
*   **Centered Glassmorphism Login**: Authenticates via Firebase Auth API and checks user permissions.
*   **Security Session Guard**: Request interceptors protect all `/cms/*` URLs.
*   **Stats Dashboard**: Key statistics and a timeline of the 10 most recent system audit logs.
*   **Audit Timelines**: System logs tracking administrator actions (IP address, action, description, timestamp).
*   **Full CRUD Modules**:
    *   *Categories*: URL slug auto-generation.
    *   *Authors*: Profile photo uploads to Firebase Storage (`storage.bucket()`).
    *   *Blogs / Courses*: Live markdown side-by-side editing panel, status triggers, and cover photo uploads.
    *   *Lessons*: Add course-specific tutorials with index order.
    *   *User Management*: Query registry directly from Firebase Auth (`list_users()`), edit statuses, and sync data.

---

## 🛠️ Tech Stack
*   **Frontend**: HTML5, Vanilla CSS3 (Outfit & Inter fonts, glassmorphism, responsive grid), JavaScript ES6.
*   **Backend**: Python 3.9+, Django 4.2.30.
*   **Database & Auth**: Google Firebase (Firestore Database, Firebase Storage).
*   **Serving**: Gunicorn (WSGI), WhiteNoise (static files with cache-busting).
*   **Deployment**: Render.com.

---

## ⚙️ Configuration & Setup

### 1. Prerequisites
Ensure you have Python 3.9+ and `venv` installed on your machine.

### 2. Environment Variables (`.env`)
Copy `.env.example` to `.env` and fill in your real values:
```bash
cp .env.example .env
```

Generate a strong `SECRET_KEY`:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Required variables:
```env
DJANGO_SECRET_KEY=your-long-random-secret-key
DEBUG=True
ALLOWED_HOSTS=*
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
FIREBASE_STORAGE_BUCKET=your-project-id.firebasestorage.app
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_API_KEY=your-firebase-web-api-key
FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
```

### 3. Firebase Credentials (`firebase-credentials.json`)
Download your Service Account private key JSON from the Firebase Console (Project Settings > Service Accounts) and save it in the root folder as `firebase-credentials.json`.

---

## 🏃 Installation & Execution

### 1. Setup Virtual Environment
Run the following commands to create the environment and install dependencies:
```bash
# Create python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 2. Run Local SQLite Migrations
Run Django migrations to create the local session cache table:
```bash
python manage.py migrate
```

### 3. Start Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```

*   **Visitor Interface**: [http://localhost:8000/](http://localhost:8000/)
*   **CMS Dashboard**: [http://localhost:8000/cms/login/](http://localhost:8000/cms/login/)

---

## 🔑 Default Administrator Credentials
*   **Admin Email**: `admin@techenablement.com`
*   **Admin Password**: `AdminPassword123!`

---

## ☁️ Deploying to Render.com

To deploy this application to **Render**, follow these steps:

1. **Push Changes to GitHub**:
   Ensure all changes are pushed to your GitHub repository:
   ```bash
   git push origin main
   ```
2. **Create a New Web Service on Render**:
   - Log into your Render dashboard and click **New > Web Service**.
   - Connect your GitHub repository.
3. **Configure Service Settings**:
   - **Runtime**: `Python`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn config.wsgi:application`
4. **Configure Environment Variables**:
   In the **Environment** tab of your Render service, add all variables defined in your local `.env` file (excluding `DEBUG=True` for security, or setting it to `False`):
   - `DJANGO_SECRET_KEY`: (generate a strong secret key)
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `your-render-app-subdomain.onrender.com`
   - `FIREBASE_PROJECT_ID`: (your Firebase project ID)
   - `FIREBASE_STORAGE_BUCKET`: (your storage bucket)
   - `FIREBASE_API_KEY`: (your Firebase Web API key)
   - `FIREBASE_AUTH_DOMAIN`: (your Firebase Auth domain)
5. **Set Firebase Service Account Credentials**:
   To securely pass the Firebase service account credentials without committing the file to Git, choose one of these methods:

   * **Option A (Recommended - Environment Variable)**:
     - On the Render dashboard, go to the **Environment** tab of your service.
     - Click **Add Environment Variable**.
     - Set the key to `FIREBASE_CREDENTIALS_JSON`.
     - Copy and paste the entire raw JSON content of your `firebase-credentials.json` file into the value text area and save.

   * **Option B (Secret File)**:
     - On the Render dashboard, go to the **Environment** tab of your service.
     - Click **Add File**.
     - Set the filename to `firebase-credentials.json`.
     - Copy and paste the entire JSON content of your local `firebase-credentials.json` into the file content text area and save.

