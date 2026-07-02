import math
from django.shortcuts import render, Http404
from config.firebase_service import db


# --- Custom Error Handlers ---

def page_not_found(request, exception=None):
    """Custom 404 handler — renders branded error page."""
    return render(request, '404.html', status=404)


def server_error(request):
    """Custom 500 handler — renders branded error page."""
    return render(request, '500.html', status=500)


def resolve_relations():
    """Helper to fetch categories and authors and return them as lookup dicts."""
    categories = {}
    authors = {}
    
    cat_docs = db.collection('categories').stream()
    for doc in cat_docs:
        categories[doc.id] = doc.to_dict()
        
    auth_docs = db.collection('authors').stream()
    for doc in auth_docs:
        authors[doc.id] = doc.to_dict()
        
    return categories, authors

def home(request):
    # Fetch published blogs and courses (sort and limit locally to avoid composite index requirements)
    blogs_ref = db.collection('blogs').where('status', '==', 'published').stream()
    courses_ref = db.collection('courses').where('status', '==', 'published').stream()
    
    categories, authors = resolve_relations()
    
    blogs_list = []
    for doc in blogs_ref:
        b = doc.to_dict()
        b['category'] = categories.get(b.get('category_id'), {'name': 'General'})
        b['author'] = authors.get(b.get('author_id'), {'name': 'Anonymous', 'profile_image': ''})
        blogs_list.append(b)
        
    # Sort by publish date descending, limit to 3
    blogs_list.sort(key=lambda x: x.get('publish_date'), reverse=True)
    blogs_list = blogs_list[:3]
        
    courses_list = []
    for doc in courses_ref:
        c = doc.to_dict()
        c['category'] = categories.get(c.get('category_id'), {'name': 'General'})
        c['author'] = authors.get(c.get('author_id'), {'name': 'Anonymous'})
        courses_list.append(c)
        
    # Sort by order ascending, limit to 3
    courses_list.sort(key=lambda x: x.get('order', 999))
    courses_list = courses_list[:3]
        
    return render(request, 'home.html', {
        'blogs': blogs_list,
        'courses': courses_list
    })

def blogs(request):
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    if page < 1:
        page = 1
        
    categories, authors = resolve_relations()
    
    # Query Firestore
    blogs_ref = db.collection('blogs').where('status', '==', 'published').stream()
    all_blogs = []
    
    for doc in blogs_ref:
        b = doc.to_dict()
        # Resolve relations
        b['category'] = categories.get(b.get('category_id'), {'name': 'General'})
        b['author'] = authors.get(b.get('author_id'), {'name': 'Anonymous', 'profile_image': ''})
        
        # Apply local filtering for search (Firestore search queries are limited)
        if query:
            q_lower = query.lower()
            if q_lower in b['title'].lower() or q_lower in b['summary'].lower() or q_lower in b.get('content', '').lower() or q_lower in b['category']['name'].lower() or q_lower in b['author']['name'].lower():
                all_blogs.append(b)
        else:
            all_blogs.append(b)
            
    # Sort by publish date descending
    all_blogs.sort(key=lambda x: x.get('publish_date'), reverse=True)
    
    # Paginate (20 blogs per page = 4 cols x 5 rows)
    per_page = 20
    total_items = len(all_blogs)
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    
    if page > total_pages:
        page = total_pages
        
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_blogs = all_blogs[start_idx:end_idx]
    
    # Page numbers list helper
    page_numbers = list(range(1, total_pages + 1))
    
    return render(request, 'blogs.html', {
        'blogs': paginated_blogs,
        'query': query,
        'page': page,
        'total_pages': total_pages,
        'page_numbers': page_numbers,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1,
        'next_page': page + 1,
    })

def blog_detail(request, slug):
    # Find blog by slug
    blogs_ref = db.collection('blogs').where('slug', '==', slug).limit(1).stream()
    blog_doc = None
    for doc in blogs_ref:
        blog_doc = doc.to_dict()
        break
        
    if not blog_doc or blog_doc.get('status') != 'published':
        raise Http404("Blog post not found")
        
    categories, authors = resolve_relations()
    blog_doc['category'] = categories.get(blog_doc.get('category_id'), {'name': 'General'})
    blog_doc['author'] = authors.get(blog_doc.get('author_id'), {'name': 'Anonymous', 'profile_image': ''})
    
    return render(request, 'blog_detail.html', {
        'blog': blog_doc
    })

def courses(request):
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    if page < 1:
        page = 1
        
    categories, authors = resolve_relations()
    
    # Query Firestore
    courses_ref = db.collection('courses').where('status', '==', 'published').stream()
    all_courses = []
    
    for doc in courses_ref:
        c = doc.to_dict()
        # Resolve relations
        c['category'] = categories.get(c.get('category_id'), {'name': 'General'})
        c['author'] = authors.get(c.get('author_id'), {'name': 'Anonymous'})
        
        # Apply search filter
        if query:
            q_lower = query.lower()
            if q_lower in c['title'].lower() or q_lower in c['summary'].lower() or q_lower in c['category']['name'].lower() or q_lower in c['author']['name'].lower():
                all_courses.append(c)
        else:
            all_courses.append(c)
            
    # Sort by order ascending
    all_courses.sort(key=lambda x: x.get('order', 999))
    
    # Paginate (20 courses per page)
    per_page = 20
    total_items = len(all_courses)
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    
    if page > total_pages:
        page = total_pages
        
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_courses = all_courses[start_idx:end_idx]
    
    page_numbers = list(range(1, total_pages + 1))
    
    return render(request, 'courses.html', {
        'courses': paginated_courses,
        'query': query,
        'page': page,
        'total_pages': total_pages,
        'page_numbers': page_numbers,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1,
        'next_page': page + 1,
    })

from django.urls import reverse

def course_detail(request, slug):
    # Find course by slug
    courses_ref = db.collection('courses').where('slug', '==', slug).limit(1).stream()
    course_data = None
    for doc in courses_ref:
        course_data = doc.to_dict()
        break
        
    if not course_data or course_data.get('status') != 'published':
        raise Http404("Course not found")
        
    # Get tutorials for this course
    tutorials_ref = db.collection('tutorials').where('course_id', '==', course_data['id']).stream()
    tutorials_list = []
    for doc in tutorials_ref:
        t = doc.to_dict()
        if t.get('status', 'published') == 'published':
            tutorials_list.append(t)
            
    # Sort by order/sequence
    tutorials_list.sort(key=lambda x: x.get('order', 1))
    
    # Calculate first tutorial URL if list is not empty
    first_tutorial_url = ""
    if tutorials_list:
        first_tutorial_url = reverse('frontend:tutorial_embed', kwargs={
            'course_slug': course_data['slug'],
            'tutorial_slug': tutorials_list[0]['slug']
        })
    
    return render(request, 'course_detail.html', {
        'course': course_data,
        'tutorials': tutorials_list,
        'first_tutorial_url': first_tutorial_url
    })

def tutorial_embed(request, course_slug, tutorial_slug):
    # Retrieve course to verify
    courses_ref = db.collection('courses').where('slug', '==', course_slug).limit(1).stream()
    course_data = None
    for doc in courses_ref:
        course_data = doc.to_dict()
        break
        
    if not course_data:
        raise Http404("Course not found")
        
    # Retrieve tutorial in course by slug
    tuts_ref = db.collection('tutorials').where('course_id', '==', course_data['id']).where('slug', '==', tutorial_slug).limit(1).stream()
    tut_data = None
    for doc in tuts_ref:
        tut_data = doc.to_dict()
        break
        
    if not tut_data:
        raise Http404("Tutorial not found")
        
    return render(request, 'tutorial_embed.html', {
        'course': course_data,
        'tutorial': tut_data
    })
