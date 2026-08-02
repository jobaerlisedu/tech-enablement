"""
seed_firebase.py
----------------
Populates the Firestore database for Tech Enablement.

This seeds:
  * categories  (5 topic areas)
  * authors     (4 contributors)
  * blogs       (24 published research blogs)
  * courses     (24 published courses)
  * tutorials   (lessons for each course)
  * superadmin  (idempotent, via seed_superuser.ensure_superuser)

It does NOT delete the 'users' collection (to preserve the superadmin).
Content collections (categories, authors, blogs, courses, tutorials,
audit_logs) are cleared first so re-runs rebuild cleanly.
"""
import os
import json
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, firestore

import dotenv
dotenv.load_dotenv()

# --- Firebase Admin SDK init (same pattern as clear_database.py) ---
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
                "Firebase credentials not found. Provide them via FIREBASE_CREDENTIALS_JSON "
                "or place firebase-credentials.json in the project root."
            )

    firebase_admin.initialize_app(cred, {
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
    })

db = firestore.client()


def _unsplash(title, category_slug=""):
    from config.firebase_service import get_unsplash_image
    return get_unsplash_image(title, category_slug)


def clear_content():
    for col in ['categories', 'authors', 'blogs', 'courses', 'tutorials', 'audit_logs']:
        deleted = 0
        for doc in db.collection(col).list_documents():
            doc.delete()
            deleted += 1
        print(f"  cleared {deleted} docs from '{col}'")


def seed_categories():
    rows = [
        ("Cybersecurity", "cybersecurity", "Vulnerability research, defense, and threat intelligence."),
        ("Cloud Computing", "cloud-computing", "Cloud infrastructure, DevOps, and distributed systems."),
        ("Artificial Intelligence", "artificial-intelligence", "Machine learning, neural networks, and applied AI."),
        ("Software Development", "software-development", "Engineering practices, languages, and tools."),
        ("Web Engineering", "web-engineering", "Modern web platforms, frameworks, and performance."),
    ]
    cat_ids = {}
    for name, slug, desc in rows:
        ref = db.collection('categories').document()
        cat_ids[slug] = ref.id
        ref.set({"id": ref.id, "name": name, "slug": slug, "description": desc})
    print("seeded categories:", len(rows))
    return cat_ids


def seed_authors():
    rows = [
        ("Dr. Ayesha Rahman", "Security researcher focused on zero-day detection.", "Security Researcher",
         "ayesha@techeablement.info"),
        ("Marcus Bennett", "Cloud architect and former SRE at a hyperscaler.", "Cloud Architect",
         "marcus@techeablement.info"),
        ("Dr. Lin Wei", "AI/ML engineer building production recommendation systems.", "ML Engineer",
         "lin@techeablement.info"),
        ("Sofia Carreón", "Full-stack engineer specializing in web performance.", "Full-Stack Engineer",
         "sofia@techeablement.info"),
    ]
    author_ids = []
    for name, bio, designation, email in rows:
        ref = db.collection('authors').document()
        author_ids.append(ref.id)
        ref.set({"id": ref.id, "name": name, "bio": bio, "designation": designation, "email": email,
                 "profile_image": ""})
    print("seeded authors len", len(author_ids))
    return author_ids


def seed_blogs(cat_ids, author_ids):
    blog_specs = [
        # (title, category_slug, author_index)
        ("Detecting Zero-Day Exploits with Behavioral Analytics", "cybersecurity", 0),
        ("Zero Trust Architecture: A Practical Blueprint", "cybersecurity", 0),
        ("Securing the Software Supply Chain in 2026", "cybersecurity", 0),
        ("The Rise of Ransomware-as-a-Service", "cybersecurity", 0),
        ("Threat Modeling for Modern Web Applications", "cybersecurity", 1),
        ("Serverless Architectures: Scaling Without Servers", "cloud-computing", 1),
        ("Kubernetes Observability Done Right", "cloud-computing", 1),
        ("Designing Multi-Cloud Disaster Recovery", "cloud-computing", 1),
        ("Cost Optimization in the Cloud", "cloud-computing", 1),
        ("Infrastructure as Code with Terraform", "cloud-computing", 2),
        ("Transformer Models in Production", "artificial-intelligence", 2),
        ("Reinforcement Learning for Autonomous Agents", "artificial-intelligence", 2),
        ("How to Evaluate LLMs Beyond Benchmarks", "artificial-intelligence", 2),
        ("Anomaly Detection with Unsupervised Learning", "artificial-intelligence", 2),
        ("The AI Engineer's Toolkit in 2026", "artificial-intelligence", 2),
        ("Clean Architecture in Python", "software-development", 3),
        ("Testing Strategies for Microservices", "software-development", 3),
        ("From Monolith to Modules: Letting Go Slowly", "software-development", 3),
        ("Effective Type Hinting in Large Codebases", "software-development", 3),
        ("Design Patterns for Data Pipelines", "software-development", 3),
        ("Rendering Performance: From Layout to Pixels", "web-engineering", 3),
        ("Accessibility as a Core Requirement", "web-engineering", 3),
        ("Building Real-Time UIs with WebSockets", "web-engineering", 3),
        ("Web Security: Headers, CSP, and CSRF", "web-engineering", 0),
    ]
    for i, (title, cat_slug, ai) in enumerate(blog_specs):
        ref = db.collection('blogs').document()
        slug = title.lower().replace(" ", "-")
        ref.set({
            "id": ref.id,
            "title": title,
            "slug": slug,
            "summary": f"Research note: {title}. Deep-dive analysis and practical guidance.",
            "content": f"# {title}\n\nThis is the full research note for **{title}**.\n\n"
                       "## Key Takeaways\n\n- Practical, vendor-neutral insights.\n- Actionable steps for teams. "
                       "- References to further reading.\n\n## Conclusion\n\nWrite and publish with your CMS here.",
            "category_id": cat_ids[cat_slug],
            "author_id": author_ids[ai],
            "status": "published",
            "cover_image": _unsplash(title, cat_slug),
            "publish_date": datetime.utcnow() - timedelta(days=i),
        })
    print(f"seeded blogs {len(blog_specs)}")


def seed_courses(cat_ids, author_ids):
    course_specs = [
        ("Ethical Hacking Fundamentals", "cybersecurity", 0, 1),
        ("Defensive Security and SOC Operations", "cybersecurity", 0, 2),
        ("Cryptography for Developers", "cybersecurity", 1, 3),
        ("Digital Forensics Essentials", "cybersecurity", 0, 4),
        ("AWS Certified Solutions Architect Prep", "cloud-computing", 1, 5),
        ("Google Cloud Networking Deep Dive", "cloud-computing", 1, 6),
        ("Containerization and Orchestration", "cloud-computing", 1, 7),
        ("Serverless Application Development", "cloud-computing", 2, 8),
        ("Monitoring and Observability", "cloud-computing", 2, 9),
        ("Machine Learning Foundations", "artificial-intelligence", 2, 10),
        ("Deep Learning with PyTorch", "artificial-intelligence", 2, 11),
        ("Model Deployment and MLflow", "artificial-intelligence", 2, 12),
        ("Natural Language Processing", "artificial-intelligence", 2, 13),
        ("Applied Computer Vision", "artificial-intelligence", 2, 14),
        ("Python for Data Science", "software-development", 3, 15),
        ("REST API Design and Testing", "software-development", 3, 16),
        ("Concurrency and Parallelism in Python", "software-development", 3, 17),
        ("Software Engineering Craftsmanship", "software-development", 3, 18),
        ("Data Engineering Essentials", "software-development", 3, 19),
        ("Modern CSS and Layout", "web-engineering", 3, 20),
        ("React with TypeScript", "web-engineering", 3, 21),
        ("Frontend Performance Optimization", "web-engineering", 3, 22),
        ("Web Security and Headers", "web-engineering", 0, 23),
        ("Progressive Web Apps", "web-engineering", 3, 24),
    ]
    for (title, cat_slug, ai, order) in course_specs:
        ref = db.collection('courses').document()
        slug = title.lower().replace(" ", "-")
        ref.set({
            "id": ref.id,
            "title": title,
            "slug": slug,
            "summary": f"A practical, project-based course on {title}.",
            "category_id": cat_ids[cat_slug],
            "author_id": author_ids[ai],
            "status": "published",
            "order": order,
            "cover_image": _unsplash(title, cat_slug),
        })
    print(f"seeded courses {len(course_specs)}")


def seed_tutorials():
    courses = {d.id: d.to_dict() for d in db.collection('courses').stream()}
    n_tuts = 0
    for cid, course in courses.items():
        # 3 lessons per course for consistency
        for lesson_no in range(1, 4):
            ref = db.collection('tutorials').document()
            title = f"{lesson_no}. {course['title'].split(' with ')[0]}: Lesson {lesson_no}"
            slug = f"{course['slug']}-lesson-{lesson_no}"
            ref.set({
                "id": ref.id,
                "course_id": cid,
                "title": title,
                "slug": slug,
                "content": f"# {title}\n\nStep-by-step lesson content for {course['title']}.\n\n"
                           "```python\nprint('Hello from Tech Enablement')\n```\n\n"
                           "Watch the next lesson to continue.",
                "order": lesson_no,
                "status": "published",
            })
            n_tuts += 1
    print(f"seeded tutorials {n_tuts}")


def main():
    print("Seeding content for Tech Enablement...")
    clear_content()
    cat_ids = seed_categories()
    author_ids = seed_authors()
    seed_blogs(cat_ids, author_ids)
    seed_courses(cat_ids, author_ids)
    seed_tutorials()

    # Ensure superadmin exists (skip if a user already exists).
    from seed_superuser import ensure_superuser
    ensure_superuser(db)
    print("Seed complete. Firestore is now populated.")


if __name__ == '__main__':
    main()