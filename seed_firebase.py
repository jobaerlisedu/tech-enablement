import os
import django
from datetime import datetime, timedelta

# Set up environment variables
import dotenv
dotenv.load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore, auth

cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': bucket_name
    })

db = firestore.client()

import re

def clean_slug(title):
    s = title.lower()
    s = s.replace('&', 'and')
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    return s.strip('-')

def seed_database():
    print("Starting Firebase seeding...")

    # 1. Clear existing collections to avoid duplicates
    collections = ['categories', 'authors', 'blogs', 'courses', 'tutorials', 'users', 'audit_logs']
    for coll_name in collections:
        docs = db.collection(coll_name).list_documents()
        deleted = 0
        for doc in docs:
            doc.delete()
            deleted += 1
        if deleted > 0:
            print(f"Cleared {deleted} documents from {coll_name}")

    # 2. Add Categories
    categories = [
        {"id": "web-dev", "name": "Web Development", "slug": "web-development", "description": "Modern frontend and backend web development techniques."},
        {"id": "ai-ml", "name": "Artificial Intelligence & ML", "slug": "ai-ml", "description": "Deep learning, machine learning, and neural network concepts."},
        {"id": "cloud-devops", "name": "Cloud & DevOps", "slug": "cloud-devops", "description": "Cloud computing, infrastructure as code, CI/CD, and scaling."},
        {"id": "security", "name": "Cybersecurity", "slug": "cybersecurity", "description": "Application security, network safety, and ethical hacking."}
    ]
    
    category_refs = {}
    for cat in categories:
        ref = db.collection('categories').document(cat['id'])
        ref.set(cat)
        category_refs[cat['id']] = cat['id']
    print(f"Seeded {len(categories)} categories.")

    # 3. Add Authors
    authors = [
        {
            "id": "alex-carter",
            "name": "Dr. Alex Carter",
            "bio": "AI Research Lead at Tech Enablement. Former researcher at MIT with 10+ years of deep learning research experience.",
            "designation": "AI Architect",
            "email": "alex.carter@example.com",
            "profile_image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=200"
        },
        {
            "id": "sarah-jenkins",
            "name": "Sarah Jenkins",
            "bio": "Senior Developer Advocate and tech writer. Enthusiastic about CSS Grid, clean code, and developer experience.",
            "designation": "Lead Developer Advocate",
            "email": "sarah.j@example.com",
            "profile_image": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=200"
        },
        {
            "id": "michael-chen",
            "name": "Michael Chen",
            "bio": "Cloud Infrastructure Engineer specializing in Kubernetes, AWS, and automation. Certified Terraform trainer.",
            "designation": "Principal DevOps Consultant",
            "email": "m.chen@example.com",
            "profile_image": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&q=80&w=200"
        }
    ]
    
    author_refs = {}
    for auth_data in authors:
        ref = db.collection('authors').document(auth_data['id'])
        ref.set(auth_data)
        author_refs[auth_data['id']] = auth_data['id']
    print(f"Seeded {len(authors)} authors.")

    # Helper lists for seeding
    cat_keys = list(category_refs.keys())
    auth_keys = list(author_refs.keys())

    # 4. Seed Blogs (Need at least 22 to test pagination 4 cols x 5 rows = 20 per page)
    blog_titles = [
        "Understanding Neural Networks: A Beginner's Guide",
        "Mastering CSS Grid and Flexbox for Modern Layouts",
        "Building Scalable Microservices with Go and gRPC",
        "A Comprehensive Guide to Firebase Authentication",
        "Understanding Django Middleware: Custom Request Pipelines",
        "Introduction to Machine Learning: Linear Regression",
        "DevOps Best Practices: CI/CD Pipelines with GitHub Actions",
        "Securing Web Applications against OWASP Top 10",
        "The Power of TypeScript: Type Safety in Javascript",
        "A Deep Dive into PostgreSQL Indexing and Optimization",
        "Introduction to Docker: Containerize Your Application",
        "Advanced React Hooks: Beyond useState and useEffect",
        "Understanding JWT Authentication: How It Works under the Hood",
        "An Overview of Kubernetes and Container Orchestration",
        "Exploring Python's Asyncio: Concurrency Made Easy",
        "How to Build an API Gateway with Node.js and Express",
        "CSS Custom Properties: Styling with CSS Variables",
        "Deep Learning with PyTorch: Your First Neural Network",
        "Deploying Django to AWS EC2: A Step-by-Step Walkthrough",
        "Introduction to Web Security: CORS, CSRF, and XSS",
        "A Complete Guide to Next.js Page Routing and SSR",
        "Building Interactive Web Graphics with Three.js",
        "Getting Started with Serverless: AWS Lambda and Serverless Framework",
        "Writing Clean Code: Principles of Maintainable Software"
    ]

    for idx, title in enumerate(blog_titles):
        slug = clean_slug(title)
        cat_id = cat_keys[idx % len(cat_keys)]
        author_id = auth_keys[idx % len(auth_keys)]
        
        # Stagger publication dates
        pub_date = datetime.now() - timedelta(days=idx)
        
        blog_data = {
            "id": f"blog-{idx+1:02d}",
            "title": title,
            "slug": slug,
            "summary": f"This is a summary of the blog post '{title}'. We explore key concepts, best practices, and practical examples to elevate your knowledge.",
            "content": f"""# {title}

Welcome to this comprehensive tutorial on **{title}**. 

In this article, we will go through everything you need to know about this subject. Learning this will significantly improve your skills as a developer and system engineer.

## Section 1: The Core Concept

Here is an example code block to demonstrate our topic:

```python
def hello_world():
    print("Welcome to {title}!")
    
hello_world()
```

## Section 2: Implementation Details

We will cover the following key topics:
- Key principle A
- Key principle B
- Troubleshooting and common pitfalls

## Conclusion

We hope you enjoyed this guide. Let us know your thoughts in the comment section!
""",
            "cover_image": f"https://picsum.photos/seed/blog_{idx+1}/800/600",
            "category_id": cat_id,
            "author_id": author_id,
            "publish_date": pub_date,
            "status": "published"
        }
        db.collection('blogs').document(blog_data['id']).set(blog_data)
    print(f"Seeded {len(blog_titles)} research blogs.")

    # 5. Seed Courses (Need at least 22 for pagination)
    course_titles = [
        "Python Django Masterclass: From Beginner to Advanced",
        "Introduction to Artificial Intelligence and Machine Learning",
        "DevOps and Cloud Engineering with AWS & Kubernetes",
        "Advanced Frontend Web Development: React & Next.js",
        "Cybersecurity Fundamentals: Protecting Web Apps",
        "Go (Golang) Programming: Build High-Performance APIs",
        "Serverless Architectures with AWS Lambda and API Gateway",
        "Mastering PostgreSQL: Architecture and Query Optimization",
        "Introduction to Docker Containers and Image Creation",
        "Building Mobile Apps with Flutter and Firebase",
        "Data Science bootcamp: NumPy, Pandas, and Matplotlib",
        "TypeScript Essentials: Statically Typed JavaScript",
        "Modern CSS: Grid, Flexbox, Tailwind, and Animations",
        "System Design: Designing Scalable Distributed Systems",
        "Building Microservices with Node.js and Docker",
        "Natural Language Processing (NLP) with Python",
        "Introduction to Terraform: Infrastructure as Code",
        "API Development with FastAPI and PostgreSQL",
        "Fullstack SaaS Development: Next.js, Stripe, & Prisma",
        "GraphQL Masterclass: Schema Design and Subscriptions",
        "Computer Vision with OpenCV and Python",
        "Git and Github: Version Control and Collaborative Workflow",
        "Asynchronous Python: Asyncio, Celery, and Redis",
        "Algorithms and Data Structures in Python"
    ]

    for idx, title in enumerate(course_titles):
        slug = clean_slug(title)
        cat_id = cat_keys[idx % len(cat_keys)]
        author_id = auth_keys[idx % len(auth_keys)]
        
        course_data = {
            "id": f"course-{idx+1:02d}",
            "title": title,
            "slug": slug,
            "summary": f"Embark on a comprehensive learning path with '{title}'. Includes videos, quizzes, assignments, and a certificate of completion.",
            "cover_image": f"https://picsum.photos/seed/course_{idx+1}/800/600",
            "category_id": cat_id,
            "author_id": author_id,
            "status": "published",
            "order": idx + 1
        }
        db.collection('courses').document(course_data['id']).set(course_data)
        
        # 6. Seed Tutorials for the first few courses (e.g. course-01, course-02, course-03)
        if idx < 3:
            tutorials = [
                {
                    "title": f"Introduction to {title}",
                    "slug": "introduction",
                    "content": f"""# Introduction to {title}

Welcome to the first lesson of this course. In this tutorial, we will introduce the core concepts of the course, discuss the prerequisites, and define our goals.

## What you will learn
1. Core concepts and terminology
2. Best practices and industry applications
3. How to build real-world systems

Let's get started!
"""
                },
                {
                    "title": "Setting Up Your Development Environment",
                    "slug": "environment-setup",
                    "content": f"""# Setting Up Your Development Environment

In this lesson, we will install all the necessary dependencies and configure our IDE for the course.

## Prerequisites
- Python 3.8+
- Node.js (if applicable)
- A text editor like VS Code

## Installing Packages
Run the following command in your terminal:
```bash
pip install -r requirements.txt
```
Make sure you see no errors before proceeding!
"""
                },
                {
                    "title": "Your First Practical Project",
                    "slug": "first-project",
                    "content": f"""# Your First Practical Project

Now that our environment is ready, let's build our first project. We will write a hello-world style module and execute it.

```python
def main():
    print("Project successfully running!")

if __name__ == '__main__':
    main()
```
Run this file and inspect the console output.
"""
                },
                {
                    "title": "Advanced Architectures and Best Practices",
                    "slug": "advanced-concepts",
                    "content": f"""# Advanced Architectures and Best Practices

In this tutorial, we explore advanced concepts, common design patterns, and structure templates that will make our project maintainable and robust.

## key Architectures
- MVC Pattern
- Event-Driven Design
- Repository Pattern
"""
                },
                {
                    "title": "Deployment, DevOps and Beyond",
                    "slug": "deployment-and-beyond",
                    "content": f"""# Deployment, DevOps and Beyond

Congratulations on reaching the final tutorial! In this lesson, we will deploy our project to production.

## Deployment checklist
- [x] Configure production settings
- [x] Run migrations
- [x] Setup static files
- [x] Deploy to Cloud

You are now a certified master of this course!
"""
                }
            ]
            
            for t_idx, tut in enumerate(tutorials):
                tut_data = {
                    "id": f"tut-{idx+1:02d}-{t_idx+1:02d}",
                    "course_id": course_data['id'],
                    "title": tut['title'],
                    "slug": tut['slug'],
                    "content": tut['content'],
                    "order": t_idx + 1,
                    "status": "published"
                }
                db.collection('tutorials').document(tut_data['id']).set(tut_data)

    print("Seeded course tutorials.")

    # 7. Create admin user in Firebase Auth and Firestore users collection
    admin_email = "admin@techenablement.com"
    admin_password = "AdminPassword123!"
    admin_uid = None

    try:
        user = auth.get_user_by_email(admin_email)
        admin_uid = user.uid
        print(f"Admin user already exists in Firebase Auth (UID: {admin_uid}).")
    except auth.UserNotFoundError:
        user = auth.create_user(
            email=admin_email,
            email_verified=True,
            password=admin_password,
            display_name="System Admin",
            disabled=False
        )
        admin_uid = user.uid
        print(f"Created admin user in Firebase Auth (UID: {admin_uid}). Credentials: {admin_email} / {admin_password}")

    # Set profile in Firestore users collection
    user_profile = {
        "uid": admin_uid,
        "email": admin_email,
        "display_name": "System Admin",
        "role": "Superadmin",
        "status": "active"
    }
    db.collection('users').document(admin_uid).set(user_profile)
    print("Admin user profile seeded in Firestore 'users' collection.")

    # Log the action in System Audit Log
    db.collection('audit_logs').add({
        "user_email": "System Seeder",
        "action": "Database Seed",
        "details": "Successfully seeded initial database configuration: 4 categories, 3 authors, 24 blogs, 24 courses, 15 tutorials, 1 superadmin.",
        "timestamp": datetime.utcnow(),
        "ip": "127.0.0.1"
    })
    
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
