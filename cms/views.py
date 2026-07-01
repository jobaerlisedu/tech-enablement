import uuid
from datetime import datetime
from django.shortcuts import render, redirect, Http404
from django.contrib import messages
from django.urls import reverse
from config.firebase_service import db, auth as firebase_auth, bucket, sign_in_with_email_and_password, log_audit
from .decorators import firebase_login_required

def upload_file_to_firebase(file, folder="uploads"):
    """Helper to upload a file to Firebase Storage and return its public URL."""
    if not bucket or not file:
        return ""
    try:
        ext = os.path.splitext(file.name)[1] if hasattr(file, 'name') else '.jpg'
        unique_name = f"{folder}/{uuid.uuid4()}{ext}"
        blob = bucket.blob(unique_name)
        blob.upload_from_file(file, content_type=file.content_type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"File upload error: {e}")
        return ""

# import os here for file extension split
import os

# --- AUTHENTICATION ---

def login_view(request):
    if request.session.get('firebase_user'):
        return redirect('cms:dashboard')
        
    error_msg = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        
        try:
            # Sign in with email and password via REST API
            token_response = sign_in_with_email_and_password(email, password)
            id_token = token_response['idToken']
            
            # Verify token on backend (allowing 60s clock skew to handle local clock variations)
            decoded_token = firebase_auth.verify_id_token(id_token, clock_skew_seconds=60)
            uid = decoded_token['uid']
            
            # Check user role in Firestore 'users'
            user_doc = db.collection('users').document(uid).get()
            if not user_doc.exists:
                # If successfully authenticated with Firebase Auth, auto-recreate profile in Firestore
                try:
                    user_record = firebase_auth.get_user(uid)
                    display_name = user_record.display_name or email.split('@')[0]
                except Exception:
                    display_name = email.split('@')[0]
                
                profile = {
                    "uid": uid,
                    "email": email,
                    "display_name": display_name,
                    "role": "Editor",
                    "status": "active"
                }
                db.collection('users').document(uid).set(profile)
                
                # Log the auto-creation
                log_audit("System", "User Profile Auto-recreated", f"Recreated profile for {email} after successful authentication", request)
            else:
                profile = user_doc.to_dict()
                
            if profile.get('status') != 'active':
                raise Exception("Your account has been deactivated.")
                
            # Store in Django session
            request.session['firebase_user'] = {
                'uid': uid,
                'email': email,
                'display_name': profile.get('display_name', email.split('@')[0]),
                'role': profile.get('role', 'Editor')
            }
            
            # Log action
            log_audit(email, "Login", "Successfully signed into the CMS dashboard", request)
            
            messages.success(request, f"Welcome back, {profile.get('display_name')}!")
            return redirect('cms:dashboard')
            
        except Exception as e:
            error_msg = str(e)
            messages.error(request, f"Authentication failed: {error_msg}")
            
    return render(request, 'cms/login.html', {'error': error_msg})

def logout_view(request):
    user = request.session.get('firebase_user')
    email = user['email'] if user else 'Unknown'
    log_audit(email, "Logout", "Logged out of the CMS dashboard", request)
    
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('cms:login')


# --- DASHBOARD ---

@firebase_login_required
def dashboard(request):
    # Fetch counts
    blogs_count = len(list(db.collection('blogs').list_documents()))
    courses_count = len(list(db.collection('courses').list_documents()))
    tutorials_count = len(list(db.collection('tutorials').list_documents()))
    categories_count = len(list(db.collection('categories').list_documents()))
    authors_count = len(list(db.collection('authors').list_documents()))
    
    # Fetch recent audit logs (latest 10)
    logs_ref = db.collection('audit_logs').order_by('timestamp', direction='DESCENDING').limit(10).stream()
    recent_logs = []
    for doc in logs_ref:
        log = doc.to_dict()
        log['id'] = doc.id
        recent_logs.append(log)
        
    context = {
        'blogs_count': blogs_count,
        'courses_count': courses_count,
        'tutorials_count': tutorials_count,
        'categories_count': categories_count,
        'authors_count': authors_count,
        'recent_logs': recent_logs
    }
    return render(request, 'cms/dashboard.html', context)


# --- CATEGORIES CRUD ---

@firebase_login_required
def category_list(request):
    cats_ref = db.collection('categories').stream()
    categories = [doc.to_dict() for doc in cats_ref]
    return render(request, 'cms/category_list.html', {'categories': categories})

@firebase_login_required
def category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip().lower().replace(" ", "-")
        description = request.POST.get('description', '').strip()
        
        if not name or not slug:
            messages.error(request, "Name and Slug are required.")
            return redirect('cms:category_add')
            
        doc_ref = db.collection('categories').document()
        cat_data = {
            'id': doc_ref.id,
            'name': name,
            'slug': slug,
            'description': description
        }
        doc_ref.set(cat_data)
        
        # Log audit
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Create Category", f"Added category '{name}' (ID: {doc_ref.id})", request)
        
        messages.success(request, f"Category '{name}' created successfully.")
        return redirect('cms:category_list')
        
    return render(request, 'cms/category_form.html', {'action': 'Create'})

@firebase_login_required
def category_edit(request, id):
    doc_ref = db.collection('categories').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Category not found")
        
    category = doc.to_dict()
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip().lower().replace(" ", "-")
        description = request.POST.get('description', '').strip()
        
        if not name or not slug:
            messages.error(request, "Name and Slug are required.")
            return redirect('cms:category_edit', id=id)
            
        doc_ref.update({
            'name': name,
            'slug': slug,
            'description': description
        })
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Edit Category", f"Updated category '{name}' (ID: {id})", request)
        
        messages.success(request, f"Category '{name}' updated successfully.")
        return redirect('cms:category_list')
        
    return render(request, 'cms/category_form.html', {'action': 'Edit', 'category': category})

@firebase_login_required
def category_delete(request, id):
    doc_ref = db.collection('categories').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Category not found")
        
    category = doc.to_dict()
    doc_ref.delete()
    
    user_email = request.session['firebase_user']['email']
    log_audit(user_email, "Delete Category", f"Deleted category '{category.get('name')}' (ID: {id})", request)
    
    messages.warning(request, f"Category '{category.get('name')}' was deleted.")
    return redirect('cms:category_list')


# --- AUTHORS CRUD ---

@firebase_login_required
def author_list(request):
    authors_ref = db.collection('authors').stream()
    authors = [doc.to_dict() for doc in authors_ref]
    return render(request, 'cms/author_list.html', {'authors': authors})

@firebase_login_required
def author_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        bio = request.POST.get('bio', '').strip()
        designation = request.POST.get('designation', '').strip()
        email = request.POST.get('email', '').strip()
        profile_image_url = request.POST.get('profile_image_url', '').strip()
        
        # Check for image file upload
        image_file = request.FILES.get('profile_image_file')
        if image_file:
            uploaded_url = upload_file_to_firebase(image_file, "authors")
            if uploaded_url:
                profile_image_url = uploaded_url
                
        if not name or not email:
            messages.error(request, "Name and Email are required.")
            return redirect('cms:author_add')
            
        doc_ref = db.collection('authors').document()
        author_data = {
            'id': doc_ref.id,
            'name': name,
            'bio': bio,
            'designation': designation,
            'email': email,
            'profile_image': profile_image_url or "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=200"
        }
        doc_ref.set(author_data)
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Create Author", f"Added author '{name}' (ID: {doc_ref.id})", request)
        
        messages.success(request, f"Author '{name}' registered successfully.")
        return redirect('cms:author_list')
        
    return render(request, 'cms/author_form.html', {'action': 'Create'})

@firebase_login_required
def author_edit(request, id):
    doc_ref = db.collection('authors').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Author not found")
        
    author = doc.to_dict()
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        bio = request.POST.get('bio', '').strip()
        designation = request.POST.get('designation', '').strip()
        email = request.POST.get('email', '').strip()
        profile_image_url = request.POST.get('profile_image_url', '').strip()
        
        # Check for image file upload
        image_file = request.FILES.get('profile_image_file')
        if image_file:
            uploaded_url = upload_file_to_firebase(image_file, "authors")
            if uploaded_url:
                profile_image_url = uploaded_url
                
        if not name or not email:
            messages.error(request, "Name and Email are required.")
            return redirect('cms:author_edit', id=id)
            
        update_data = {
            'name': name,
            'bio': bio,
            'designation': designation,
            'email': email
        }
        if profile_image_url:
            update_data['profile_image'] = profile_image_url
            
        doc_ref.update(update_data)
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Edit Author", f"Updated author '{name}' (ID: {id})", request)
        
        messages.success(request, f"Author '{name}' updated successfully.")
        return redirect('cms:author_list')
        
    return render(request, 'cms/author_form.html', {'action': 'Edit', 'author': author})

@firebase_login_required
def author_delete(request, id):
    doc_ref = db.collection('authors').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Author not found")
        
    author = doc.to_dict()
    doc_ref.delete()
    
    user_email = request.session['firebase_user']['email']
    log_audit(user_email, "Delete Author", f"Deleted author '{author.get('name')}' (ID: {id})", request)
    
    messages.warning(request, f"Author '{author.get('name')}' was deleted.")
    return redirect('cms:author_list')


# --- RESEARCH BLOGS CRUD ---

@firebase_login_required
def blog_list(request):
    blogs_ref = db.collection('blogs').stream()
    blogs = []
    
    # Pre-resolve categories & authors for listing
    cats_ref = db.collection('categories').stream()
    cats = {doc.id: doc.to_dict() for doc in cats_ref}
    auths_ref = db.collection('authors').stream()
    auths = {doc.id: doc.to_dict() for doc in auths_ref}
    
    for doc in blogs_ref:
        b = doc.to_dict()
        b['category'] = cats.get(b.get('category_id'), {'name': 'General'})
        b['author'] = auths.get(b.get('author_id'), {'name': 'Anonymous'})
        blogs.append(b)
        
    # Sort by publish date descending
    blogs.sort(key=lambda x: x.get('publish_date') or datetime.min, reverse=True)
    return render(request, 'cms/blog_list.html', {'blogs': blogs})

@firebase_login_required
def blog_add(request):
    cats_ref = db.collection('categories').stream()
    categories = [doc.to_dict() for doc in cats_ref]
    auths_ref = db.collection('authors').stream()
    authors = [doc.to_dict() for doc in auths_ref]
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        slug = request.POST.get('slug', '').strip().lower().replace(" ", "-")
        summary = request.POST.get('summary', '').strip()
        content = request.POST.get('content', '').strip()
        category_id = request.POST.get('category_id', '').strip()
        author_id = request.POST.get('author_id', '').strip()
        status = request.POST.get('status', 'draft').strip()
        cover_image = request.POST.get('cover_image', '').strip()
        
        # File upload
        cover_file = request.FILES.get('cover_file')
        if cover_file:
            uploaded_url = upload_file_to_firebase(cover_file, "blogs")
            if uploaded_url:
                cover_image = uploaded_url
                
        if not title or not slug:
            messages.error(request, "Title and Slug are required.")
            return redirect('cms:blog_add')
            
        doc_ref = db.collection('blogs').document()
        blog_data = {
            'id': doc_ref.id,
            'title': title,
            'slug': slug,
            'summary': summary,
            'content': content,
            'category_id': category_id,
            'author_id': author_id,
            'status': status,
            'cover_image': cover_image or "https://picsum.photos/800/600",
            'publish_date': datetime.utcnow()
        }
        doc_ref.set(blog_data)
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Create Blog", f"Added blog '{title}' (ID: {doc_ref.id})", request)
        
        messages.success(request, f"Blog post '{title}' published successfully.")
        return redirect('cms:blog_list')
        
    return render(request, 'cms/blog_form.html', {
        'action': 'Create',
        'categories': categories,
        'authors': authors
    })

@firebase_login_required
def blog_edit(request, id):
    doc_ref = db.collection('blogs').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Blog not found")
        
    blog = doc.to_dict()
    
    cats_ref = db.collection('categories').stream()
    categories = [doc.to_dict() for doc in cats_ref]
    auths_ref = db.collection('authors').stream()
    authors = [doc.to_dict() for doc in auths_ref]
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        slug = request.POST.get('slug', '').strip().lower().replace(" ", "-")
        summary = request.POST.get('summary', '').strip()
        content = request.POST.get('content', '').strip()
        category_id = request.POST.get('category_id', '').strip()
        author_id = request.POST.get('author_id', '').strip()
        status = request.POST.get('status', 'draft').strip()
        cover_image = request.POST.get('cover_image', '').strip()
        
        # File upload
        cover_file = request.FILES.get('cover_file')
        if cover_file:
            uploaded_url = upload_file_to_firebase(cover_file, "blogs")
            if uploaded_url:
                cover_image = uploaded_url
                
        if not title or not slug:
            messages.error(request, "Title and Slug are required.")
            return redirect('cms:blog_edit', id=id)
            
        update_data = {
            'title': title,
            'slug': slug,
            'summary': summary,
            'content': content,
            'category_id': category_id,
            'author_id': author_id,
            'status': status
        }
        if cover_image:
            update_data['cover_image'] = cover_image
            
        doc_ref.update(update_data)
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Edit Blog", f"Updated blog '{title}' (ID: {id})", request)
        
        messages.success(request, f"Blog post '{title}' updated successfully.")
        return redirect('cms:blog_list')
        
    return render(request, 'cms/blog_form.html', {
        'action': 'Edit',
        'blog': blog,
        'categories': categories,
        'authors': authors
    })

@firebase_login_required
def blog_delete(request, id):
    doc_ref = db.collection('blogs').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Blog not found")
        
    blog = doc.to_dict()
    doc_ref.delete()
    
    user_email = request.session['firebase_user']['email']
    log_audit(user_email, "Delete Blog", f"Deleted blog '{blog.get('title')}' (ID: {id})", request)
    
    messages.warning(request, f"Blog '{blog.get('title')}' was deleted.")
    return redirect('cms:blog_list')


# --- COURSES CRUD ---

@firebase_login_required
def course_list(request):
    courses_ref = db.collection('courses').stream()
    courses = []
    
    cats_ref = db.collection('categories').stream()
    cats = {doc.id: doc.to_dict() for doc in cats_ref}
    auths_ref = db.collection('authors').stream()
    auths = {doc.id: doc.to_dict() for doc in auths_ref}
    
    for doc in courses_ref:
        c = doc.to_dict()
        c['category'] = cats.get(c.get('category_id'), {'name': 'General'})
        c['author'] = auths.get(c.get('author_id'), {'name': 'Anonymous'})
        courses.append(c)
        
    courses.sort(key=lambda x: x.get('order', 999))
    return render(request, 'cms/course_list.html', {'courses': courses})

@firebase_login_required
def course_add(request):
    cats_ref = db.collection('categories').stream()
    categories = [doc.to_dict() for doc in cats_ref]
    auths_ref = db.collection('authors').stream()
    authors = [doc.to_dict() for doc in auths_ref]
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        slug = request.POST.get('slug', '').strip().lower().replace(" ", "-")
        summary = request.POST.get('summary', '').strip()
        category_id = request.POST.get('category_id', '').strip()
        author_id = request.POST.get('author_id', '').strip()
        status = request.POST.get('status', 'draft').strip()
        order = int(request.POST.get('order', 1))
        cover_image = request.POST.get('cover_image', '').strip()
        
        # File upload
        cover_file = request.FILES.get('cover_file')
        if cover_file:
            uploaded_url = upload_file_to_firebase(cover_file, "courses")
            if uploaded_url:
                cover_image = uploaded_url
                
        if not title or not slug:
            messages.error(request, "Title and Slug are required.")
            return redirect('cms:course_add')
            
        doc_ref = db.collection('courses').document()
        course_data = {
            'id': doc_ref.id,
            'title': title,
            'slug': slug,
            'summary': summary,
            'category_id': category_id,
            'author_id': author_id,
            'status': status,
            'order': order,
            'cover_image': cover_image or "https://picsum.photos/800/600"
        }
        doc_ref.set(course_data)
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Create Course", f"Added course '{title}' (ID: {doc_ref.id})", request)
        
        messages.success(request, f"Course '{title}' added successfully.")
        return redirect('cms:course_list')
        
    return render(request, 'cms/course_form.html', {
        'action': 'Create',
        'categories': categories,
        'authors': authors
    })

@firebase_login_required
def course_edit(request, id):
    doc_ref = db.collection('courses').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Course not found")
        
    course = doc.to_dict()
    
    cats_ref = db.collection('categories').stream()
    categories = [doc.to_dict() for doc in cats_ref]
    auths_ref = db.collection('authors').stream()
    authors = [doc.to_dict() for doc in auths_ref]
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        slug = request.POST.get('slug', '').strip().lower().replace(" ", "-")
        summary = request.POST.get('summary', '').strip()
        category_id = request.POST.get('category_id', '').strip()
        author_id = request.POST.get('author_id', '').strip()
        status = request.POST.get('status', 'draft').strip()
        order = int(request.POST.get('order', 1))
        cover_image = request.POST.get('cover_image', '').strip()
        
        # File upload
        cover_file = request.FILES.get('cover_file')
        if cover_file:
            uploaded_url = upload_file_to_firebase(cover_file, "courses")
            if uploaded_url:
                cover_image = uploaded_url
                
        if not title or not slug:
            messages.error(request, "Title and Slug are required.")
            return redirect('cms:course_edit', id=id)
            
        update_data = {
            'title': title,
            'slug': slug,
            'summary': summary,
            'category_id': category_id,
            'author_id': author_id,
            'status': status,
            'order': order
        }
        if cover_image:
            update_data['cover_image'] = cover_image
            
        doc_ref.update(update_data)
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Edit Course", f"Updated course '{title}' (ID: {id})", request)
        
        messages.success(request, f"Course '{title}' updated successfully.")
        return redirect('cms:course_list')
        
    return render(request, 'cms/course_form.html', {
        'action': 'Edit',
        'course': course,
        'categories': categories,
        'authors': authors
    })

@firebase_login_required
def course_delete(request, id):
    doc_ref = db.collection('courses').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Course not found")
        
    course = doc.to_dict()
    
    # Delete related tutorials first
    tuts_ref = db.collection('tutorials').where('course_id', '==', id).stream()
    deleted_tuts = 0
    for doc_tut in tuts_ref:
        doc_tut.reference.delete()
        deleted_tuts += 1
        
    doc_ref.delete()
    
    user_email = request.session['firebase_user']['email']
    log_audit(user_email, "Delete Course", f"Deleted course '{course.get('title')}' (ID: {id}) and {deleted_tuts} tutorials", request)
    
    messages.warning(request, f"Course '{course.get('title')}' and its tutorials were deleted.")
    return redirect('cms:course_list')


# --- TUTORIALS CRUD ---

@firebase_login_required
def tutorial_list(request):
    tuts_ref = db.collection('tutorials').stream()
    tutorials = []
    
    courses_ref = db.collection('courses').stream()
    courses_dict = {doc.id: doc.to_dict() for doc in courses_ref}
    
    for doc in tuts_ref:
        t = doc.to_dict()
        t['course'] = courses_dict.get(t.get('course_id'), {'title': 'Unknown Course'})
        tutorials.append(t)
        
    # Sort by Course Title then Tutorial Order
    tutorials.sort(key=lambda x: (x['course'].get('title', ''), x.get('order', 1)))
    return render(request, 'cms/tutorial_list.html', {'tutorials': tutorials})

@firebase_login_required
def tutorial_add(request):
    courses_ref = db.collection('courses').stream()
    courses = [doc.to_dict() for doc in courses_ref]
    
    if request.method == 'POST':
        course_id = request.POST.get('course_id', '').strip()
        title = request.POST.get('title', '').strip()
        slug = request.POST.get('slug', '').strip().lower().replace(" ", "-")
        content = request.POST.get('content', '').strip()
        order = int(request.POST.get('order', 1))
        status = request.POST.get('status', 'published').strip()
        
        if not course_id or not title or not slug:
            messages.error(request, "Course, Title and Slug are required.")
            return redirect('cms:tutorial_add')
            
        doc_ref = db.collection('tutorials').document()
        tut_data = {
            'id': doc_ref.id,
            'course_id': course_id,
            'title': title,
            'slug': slug,
            'content': content,
            'order': order,
            'status': status
        }
        doc_ref.set(tut_data)
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Create Tutorial", f"Added tutorial '{title}' (ID: {doc_ref.id}) to course {course_id}", request)
        
        messages.success(request, f"Tutorial '{title}' added successfully.")
        return redirect('cms:tutorial_list')
        
    return render(request, 'cms/tutorial_form.html', {
        'action': 'Create',
        'courses': courses
    })

@firebase_login_required
def tutorial_edit(request, id):
    doc_ref = db.collection('tutorials').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Tutorial not found")
        
    tutorial = doc.to_dict()
    courses_ref = db.collection('courses').stream()
    courses = [doc.to_dict() for doc in courses_ref]
    
    if request.method == 'POST':
        course_id = request.POST.get('course_id', '').strip()
        title = request.POST.get('title', '').strip()
        slug = request.POST.get('slug', '').strip().lower().replace(" ", "-")
        content = request.POST.get('content', '').strip()
        order = int(request.POST.get('order', 1))
        status = request.POST.get('status', 'published').strip()
        
        if not course_id or not title or not slug:
            messages.error(request, "Course, Title and Slug are required.")
            return redirect('cms:tutorial_edit', id=id)
            
        doc_ref.update({
            'course_id': course_id,
            'title': title,
            'slug': slug,
            'content': content,
            'order': order,
            'status': status
        })
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Edit Tutorial", f"Updated tutorial '{title}' (ID: {id})", request)
        
        messages.success(request, f"Tutorial '{title}' updated successfully.")
        return redirect('cms:tutorial_list')
        
    return render(request, 'cms/tutorial_form.html', {
        'action': 'Edit',
        'tutorial': tutorial,
        'courses': courses
    })

@firebase_login_required
def tutorial_delete(request, id):
    doc_ref = db.collection('tutorials').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("Tutorial not found")
        
    tutorial = doc.to_dict()
    doc_ref.delete()
    
    user_email = request.session['firebase_user']['email']
    log_audit(user_email, "Delete Tutorial", f"Deleted tutorial '{tutorial.get('title')}' (ID: {id})", request)
    
    messages.warning(request, f"Tutorial '{tutorial.get('title')}' was deleted.")
    return redirect('cms:tutorial_list')


# --- USERS CRUD ---

@firebase_login_required
def user_list(request):
    try:
        # 1. Fetch all users from Firebase Auth directly
        auth_users_page = firebase_auth.list_users()
        users = []
        
        # Get all current Firestore profiles to map/reconcile locally
        firestore_users = {doc.id: doc.to_dict() for doc in db.collection('users').stream()}
        
        for auth_user in auth_users_page.users:
            uid = auth_user.uid
            email = auth_user.email
            display_name = auth_user.display_name or (email.split('@')[0] if email else "Unnamed User")
            
            # Retrieve or auto-heal Firestore profile
            profile = firestore_users.get(uid)
            if not profile:
                role = 'Superadmin' if email == 'admin@techenablement.com' else 'Editor'
                status = 'inactive' if auth_user.disabled else 'active'
                profile = {
                    'uid': uid,
                    'email': email,
                    'display_name': display_name,
                    'role': role,
                    'status': status
                }
                db.collection('users').document(uid).set(profile)
            else:
                # Sync Firestore status if it doesn't match the current Auth state
                expected_status = 'inactive' if auth_user.disabled else 'active'
                if profile.get('status') != expected_status:
                    profile['status'] = expected_status
                    db.collection('users').document(uid).update({'status': expected_status})
            
            users.append(profile)
            
        return render(request, 'cms/user_list.html', {'users': users})
    except Exception as e:
        messages.error(request, f"Failed to list users from Firebase Auth: {str(e)}")
        # Fallback to pure Firestore query
        users_ref = db.collection('users').stream()
        users = [doc.to_dict() for doc in users_ref]
        return render(request, 'cms/user_list.html', {'users': users})

@firebase_login_required
def user_add(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        role = request.POST.get('role', 'Editor').strip()
        status = request.POST.get('status', 'active').strip()
        
        if not email or not password or not display_name:
            messages.error(request, "Email, Password, and Display Name are required.")
            return redirect('cms:user_add')
            
        try:
            # 1. Create in Firebase Auth with the disabled status set directly
            auth_user = firebase_auth.create_user(
                email=email,
                password=password,
                display_name=display_name,
                disabled=(status == 'inactive')
            )
            uid = auth_user.uid
            
            # 2. Save in Firestore users collection
            user_data = {
                'uid': uid,
                'email': email,
                'display_name': display_name,
                'role': role,
                'status': status
            }
            db.collection('users').document(uid).set(user_data)
            
            user_email = request.session['firebase_user']['email']
            log_audit(user_email, "Create CMS User", f"Created CMS user '{display_name}' ({email}) (UID: {uid})", request)
            
            messages.success(request, f"CMS User '{display_name}' created successfully in Auth & Database.")
            return redirect('cms:user_list')
        except Exception as e:
            messages.error(request, f"Failed to create user: {str(e)}")
            return redirect('cms:user_add')
            
    return render(request, 'cms/user_form.html', {'action': 'Create'})

@firebase_login_required
def user_edit(request, id):  # id is the UID
    doc_ref = db.collection('users').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("CMS User not found")
        
    user = doc.to_dict()
    
    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        role = request.POST.get('role', 'Editor').strip()
        status = request.POST.get('status', 'active').strip()
        password = request.POST.get('password', '').strip()
        
        if not display_name:
            messages.error(request, "Display Name is required.")
            return redirect('cms:user_edit', id=id)
            
        try:
            # 1. Update in Firebase Auth
            update_args = {'display_name': display_name}
            if password:
                update_args['password'] = password
            if status == 'active':
                update_args['disabled'] = False
            else:
                update_args['disabled'] = True
                
            firebase_auth.update_user(id, **update_args)
            
            # 2. Update Firestore profile
            doc_ref.update({
                'display_name': display_name,
                'role': role,
                'status': status
            })
            
            user_email = request.session['firebase_user']['email']
            log_audit(user_email, "Edit CMS User", f"Updated CMS user '{display_name}' (UID: {id})", request)
            
            messages.success(request, f"CMS User '{display_name}' updated successfully.")
            return redirect('cms:user_list')
        except Exception as e:
            messages.error(request, f"Failed to update user: {str(e)}")
            return redirect('cms:user_edit', id=id)
            
    return render(request, 'cms/user_form.html', {'action': 'Edit', 'cms_user': user})

@firebase_login_required
def user_delete(request, id):  # id is the UID
    doc_ref = db.collection('users').document(id)
    doc = doc_ref.get()
    if not doc.exists:
        raise Http404("CMS User not found")
        
    user = doc.to_dict()
    
    # Prevent self-deletion
    if id == request.session['firebase_user']['uid']:
        messages.error(request, "You cannot delete your own CMS account.")
        return redirect('cms:user_list')
        
    try:
        # 1. Delete in Firebase Auth
        firebase_auth.delete_user(id)
        
        # 2. Delete Firestore profile
        doc_ref.delete()
        
        user_email = request.session['firebase_user']['email']
        log_audit(user_email, "Delete CMS User", f"Deleted CMS user '{user.get('display_name')}' ({user.get('email')})", request)
        
        messages.warning(request, f"CMS User '{user.get('display_name')}' deleted successfully.")
    except Exception as e:
        messages.error(request, f"Failed to delete user from Firebase Auth: {str(e)}")
        
    return redirect('cms:user_list')


# --- SYSTEM AUDIT LOGS ---

@firebase_login_required
def audit_logs(request):
    # Fetch all audit logs, ordered by timestamp descending
    logs_ref = db.collection('audit_logs').order_by('timestamp', direction='DESCENDING').stream()
    logs = []
    for doc in logs_ref:
        log = doc.to_dict()
        log['id'] = doc.id
        logs.append(log)
        
    return render(request, 'cms/audit_logs.html', {'logs': logs})


# --- CMS DOCUMENTATION ---

@firebase_login_required
def docs(request):
    return render(request, 'cms/docs.html')
