"""Populate database with comprehensive dummy data."""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.candidate import (
    Candidate, CandidateContact, CandidatePreference, CandidateDemographics,
    CandidateResume, Skill, CandidateSkill, Job, Application, ApplicationStatus, JobStatus
)
import random
from app.services.embeddings import embedding_service
from app.services.vector_store import vector_store
from app.services.s3_client import s3_client

# Force UTF-8 encoding for console output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


# Dummy jobs with diverse requirements
DUMMY_JOBS = [
    {
        "title": "Senior Python Engineer",
        "description": """We're looking for an experienced Python engineer to join our backend team.
        You'll be building scalable microservices using FastAPI, working with PostgreSQL databases,
        and deploying to AWS cloud infrastructure. Experience with Docker and CI/CD pipelines is essential.

        Responsibilities:
        - Design and implement RESTful APIs using FastAPI
        - Optimize database queries and schema design
        - Build containerized applications with Docker
        - Collaborate with frontend team on API contracts
        - Mentor junior developers

        Our tech stack: Python, FastAPI, PostgreSQL, Redis, Docker, AWS, React""",
        "department": "Engineering",
        "location": "San Francisco, CA (Hybrid)",
        "status": JobStatus.open,
        "required_skills_json": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "REST APIs"],
        "must_have_skills_json": ["Python", "PostgreSQL"],
        "min_years_experience": 5.0,
        "max_years_experience": 10.0,
        "work_arrangement": "hybrid",
        "employment_type": "full-time"
    },
    {
        "title": "Full-Stack Engineer (React + Python)",
        "description": """Join our product team as a full-stack engineer working on customer-facing features.
        You'll build responsive UIs with React/TypeScript and backend services with Python.

        Key Responsibilities:
        - Develop modern React applications with TypeScript
        - Build RESTful APIs with Python (FastAPI/Django)
        - Implement real-time features using WebSockets
        - Write comprehensive tests (Jest, Pytest)
        - Participate in code reviews and architecture discussions

        Tech Stack: React, TypeScript, Python, FastAPI, PostgreSQL, Redis, AWS""",
        "department": "Product Engineering",
        "location": "Remote (US Only)",
        "status": JobStatus.open,
        "required_skills_json": ["React", "TypeScript", "Python", "FastAPI", "PostgreSQL"],
        "must_have_skills_json": ["React", "Python"],
        "min_years_experience": 3.0,
        "max_years_experience": 8.0,
        "work_arrangement": "remote",
        "employment_type": "full-time"
    },
    {
        "title": "Data Engineer - Big Data Platform",
        "description": """Build and maintain our data infrastructure handling billions of events daily.
        Work with modern big data technologies including Spark, Kafka, and cloud data warehouses.

        What You'll Do:
        - Design and implement data pipelines using Apache Spark
        - Build real-time streaming applications with Kafka
        - Optimize data warehouse performance (Snowflake/Redshift)
        - Develop ETL processes in Python/Scala
        - Monitor and troubleshoot data quality issues

        Technologies: Python, Spark, Kafka, SQL, AWS, Airflow, Snowflake""",
        "department": "Data Platform",
        "location": "Austin, TX (Hybrid)",
        "status": JobStatus.open,
        "required_skills_json": ["Python", "Spark", "Kafka", "SQL", "AWS", "ETL"],
        "must_have_skills_json": ["Python", "Spark", "SQL"],
        "min_years_experience": 4.0,
        "max_years_experience": 12.0,
        "work_arrangement": "hybrid",
        "employment_type": "full-time"
    },
    {
        "title": "Java Backend Engineer - Microservices",
        "description": """Looking for a Java expert to work on our microservices architecture.
        You'll design distributed systems using Spring Boot, implement event-driven patterns,
        and ensure high availability and scalability.

        Responsibilities:
        - Build microservices with Spring Boot and Spring Cloud
        - Design event-driven architectures using Kafka
        - Implement API gateways and service mesh
        - Optimize performance and troubleshoot production issues
        - Lead technical design discussions

        Stack: Java, Spring Boot, Kafka, PostgreSQL, Redis, Kubernetes, AWS""",
        "department": "Platform Engineering",
        "location": "Seattle, WA (Onsite)",
        "status": JobStatus.open,
        "required_skills_json": ["Java", "Spring Boot", "Microservices", "Kafka", "Kubernetes"],
        "must_have_skills_json": ["Java", "Spring Boot"],
        "min_years_experience": 5.0,
        "max_years_experience": 10.0,
        "work_arrangement": "onsite",
        "employment_type": "full-time"
    },
    {
        "title": "DevOps Engineer - Cloud Infrastructure",
        "description": """Manage and scale our cloud infrastructure on AWS. Build automation tools,
        implement CI/CD pipelines, and ensure system reliability.

        Key Duties:
        - Manage AWS infrastructure (EC2, RDS, S3, Lambda)
        - Build CI/CD pipelines with GitHub Actions
        - Implement Infrastructure as Code (Terraform)
        - Set up monitoring and alerting (Datadog, CloudWatch)
        - Troubleshoot production incidents

        Required Skills: AWS, Docker, Kubernetes, Terraform, Python, Linux""",
        "department": "Infrastructure",
        "location": "Remote (Global)",
        "status": JobStatus.open,
        "required_skills_json": ["AWS", "Docker", "Kubernetes", "Terraform", "Python", "Linux"],
        "must_have_skills_json": ["AWS", "Docker"],
        "min_years_experience": 3.0,
        "max_years_experience": 8.0,
        "work_arrangement": "remote",
        "employment_type": "full-time"
    },
    {
        "title": "Machine Learning Engineer",
        "description": """Build and deploy ML models for our recommendation and ranking systems.
        Work with large-scale datasets and implement production ML pipelines.

        What You'll Work On:
        - Develop ML models using PyTorch/TensorFlow
        - Build feature engineering pipelines
        - Deploy models to production using MLflow/Kubeflow
        - A/B test model improvements
        - Collaborate with data scientists on research

        Tech Stack: Python, PyTorch, Scikit-learn, Spark, AWS, Docker""",
        "department": "Machine Learning",
        "location": "San Francisco, CA (Hybrid)",
        "status": JobStatus.open,
        "required_skills_json": ["Python", "Machine Learning", "PyTorch", "AWS", "Docker"],
        "must_have_skills_json": ["Python", "Machine Learning"],
        "min_years_experience": 3.0,
        "max_years_experience": 7.0,
        "work_arrangement": "hybrid",
        "employment_type": "full-time"
    }
]


# Dummy candidates with diverse profiles
DUMMY_CANDIDATES = [
    {
        "full_name": "Sarah Chen",
        "years_experience": 8.0,
        "professional_summary": "Senior Full-Stack Engineer with expertise in Python, React, and cloud architecture. Led multiple high-impact projects at tech startups. Passionate about building scalable systems and mentoring junior developers.",
        "contact": {"email": "sarah.chen@example.com", "phone": "+1-415-555-0101", "city": "San Francisco", "region": "CA", "country": "US"},
        "skills": [
            {"name": "Python", "level": "Expert", "years": 8.0},
            {"name": "React", "level": "Expert", "years": 6.0},
            {"name": "PostgreSQL", "level": "Advanced", "years": 7.0},
            {"name": "AWS", "level": "Advanced", "years": 5.0},
            {"name": "Docker", "level": "Advanced", "years": 4.0},
            {"name": "FastAPI", "level": "Advanced", "years": 3.0},
            {"name": "TypeScript", "level": "Advanced", "years": 5.0}
        ],
        "education": [
            {"institution": "Stanford University", "degree": "MS", "field_of_study": "Computer Science", "graduation_year": 2016}
        ],
        "experience": [
            {"company": "TechCorp", "title": "Senior Software Engineer", "start_date": datetime(2020, 1, 1), "end_date": None, "description": "Leading backend team, architecting microservices"},
            {"company": "StartupXYZ", "title": "Software Engineer", "start_date": datetime(2016, 6, 1), "end_date": datetime(2019, 12, 31), "description": "Full-stack development"}
        ]
    },
    {
        "full_name": "Michael Rodriguez",
        "years_experience": 5.0,
        "professional_summary": "Data Engineer specializing in big data pipelines and ML infrastructure. Experience with Spark, Kafka, and modern data warehousing. Strong background in Python and SQL optimization.",
        "contact": {"email": "m.rodriguez@example.com", "phone": "+1-512-555-0202", "city": "Austin", "region": "TX", "country": "US"},
        "skills": [
            {"name": "Python", "level": "Expert", "years": 5.0},
            {"name": "SQL", "level": "Expert", "years": 5.0},
            {"name": "Apache Spark", "level": "Advanced", "years": 3.0},
            {"name": "Kafka", "level": "Advanced", "years": 2.0},
            {"name": "AWS", "level": "Intermediate", "years": 3.0},
            {"name": "PostgreSQL", "level": "Advanced", "years": 4.0},
            {"name": "Docker", "level": "Intermediate", "years": 2.0}
        ],
        "education": [
            {"institution": "UT Austin", "degree": "BS", "field_of_study": "Computer Science", "graduation_year": 2019}
        ],
        "experience": [
            {"company": "DataCo", "title": "Data Engineer", "start_date": datetime(2019, 7, 1), "end_date": None, "description": "Building ETL pipelines and data lakes"}
        ]
    },
    {
        "full_name": "Emily Watson",
        "years_experience": 12.0,
        "professional_summary": "Engineering Manager with deep technical background in distributed systems. Previously Staff Engineer at major tech companies. Expertise in Java, Go, and system design. Proven track record of scaling teams and products.",
        "contact": {"email": "emily.w@example.com", "phone": "+1-206-555-0303", "city": "Seattle", "region": "WA", "country": "US"},
        "skills": [
            {"name": "Java", "level": "Expert", "years": 12.0},
            {"name": "Go", "level": "Expert", "years": 6.0},
            {"name": "Kubernetes", "level": "Expert", "years": 5.0},
            {"name": "System Design", "level": "Expert", "years": 10.0},
            {"name": "Python", "level": "Advanced", "years": 8.0},
            {"name": "PostgreSQL", "level": "Advanced", "years": 10.0},
            {"name": "Redis", "level": "Advanced", "years": 7.0}
        ],
        "education": [
            {"institution": "MIT", "degree": "MS", "field_of_study": "Computer Science", "graduation_year": 2012}
        ],
        "experience": [
            {"company": "MegaCorp", "title": "Engineering Manager", "start_date": datetime(2021, 1, 1), "end_date": None, "description": "Leading 15-person engineering team"},
            {"company": "TechGiant", "title": "Staff Engineer", "start_date": datetime(2015, 3, 1), "end_date": datetime(2020, 12, 31), "description": "Distributed systems architecture"}
        ]
    },
    {
        "full_name": "David Kim",
        "years_experience": 3.0,
        "professional_summary": "Frontend Engineer focused on React and modern web technologies. Strong eye for UI/UX. Recently completed bootcamp and gained 3 years of professional experience building consumer-facing applications.",
        "contact": {"email": "david.kim@example.com", "phone": "+1-347-555-0404", "city": "New York", "region": "NY", "country": "US"},
        "skills": [
            {"name": "React", "level": "Advanced", "years": 3.0},
            {"name": "JavaScript", "level": "Advanced", "years": 3.0},
            {"name": "TypeScript", "level": "Intermediate", "years": 2.0},
            {"name": "CSS", "level": "Advanced", "years": 3.0},
            {"name": "HTML", "level": "Expert", "years": 3.0},
            {"name": "Node.js", "level": "Intermediate", "years": 2.0}
        ],
        "education": [
            {"institution": "General Assembly", "degree": "Certificate", "field_of_study": "Software Engineering", "graduation_year": 2021}
        ],
        "experience": [
            {"company": "WebStartup", "title": "Frontend Engineer", "start_date": datetime(2021, 8, 1), "end_date": None, "description": "Building responsive web applications"}
        ]
    },
    {
        "full_name": "Priya Patel",
        "years_experience": 6.0,
        "professional_summary": "DevOps Engineer with strong automation and infrastructure-as-code skills. Experience with AWS, Terraform, and CI/CD pipelines. Reduced deployment time by 70% through automation initiatives.",
        "contact": {"email": "priya.patel@example.com", "phone": "+1-650-555-0505", "city": "Palo Alto", "region": "CA", "country": "US"},
        "skills": [
            {"name": "AWS", "level": "Expert", "years": 6.0},
            {"name": "Terraform", "level": "Expert", "years": 4.0},
            {"name": "Docker", "level": "Expert", "years": 5.0},
            {"name": "Kubernetes", "level": "Advanced", "years": 3.0},
            {"name": "Python", "level": "Advanced", "years": 5.0},
            {"name": "Bash", "level": "Expert", "years": 6.0},
            {"name": "Jenkins", "level": "Advanced", "years": 4.0}
        ],
        "education": [
            {"institution": "UC Berkeley", "degree": "BS", "field_of_study": "Electrical Engineering", "graduation_year": 2018}
        ],
        "experience": [
            {"company": "CloudTech", "title": "Senior DevOps Engineer", "start_date": datetime(2021, 3, 1), "end_date": None, "description": "Infrastructure automation and cloud migration"},
            {"company": "StartupABC", "title": "DevOps Engineer", "start_date": datetime(2018, 6, 1), "end_date": datetime(2021, 2, 28), "description": "CI/CD pipeline development"}
        ]
    },
    {
        "full_name": "James Thompson",
        "years_experience": 15.0,
        "professional_summary": "Principal Engineer and architecture consultant. Deep expertise in microservices, event-driven systems, and scalability. Architected systems handling 1B+ requests/day. Mentor and technical advisor.",
        "contact": {"email": "j.thompson@example.com", "phone": "+1-617-555-0606", "city": "Boston", "region": "MA", "country": "US"},
        "skills": [
            {"name": "System Design", "level": "Expert", "years": 15.0},
            {"name": "Java", "level": "Expert", "years": 15.0},
            {"name": "Python", "level": "Expert", "years": 10.0},
            {"name": "Kubernetes", "level": "Expert", "years": 7.0},
            {"name": "PostgreSQL", "level": "Expert", "years": 15.0},
            {"name": "Redis", "level": "Expert", "years": 10.0},
            {"name": "Kafka", "level": "Expert", "years": 8.0},
            {"name": "AWS", "level": "Expert", "years": 12.0}
        ],
        "education": [
            {"institution": "Carnegie Mellon", "degree": "PhD", "field_of_study": "Computer Science", "graduation_year": 2009}
        ],
        "experience": [
            {"company": "TechConsulting", "title": "Principal Engineer", "start_date": datetime(2018, 1, 1), "end_date": None, "description": "Architecture consulting for Fortune 500 companies"},
            {"company": "BigTech", "title": "Senior Staff Engineer", "start_date": datetime(2010, 6, 1), "end_date": datetime(2017, 12, 31), "description": "Distributed systems at scale"}
        ]
    },
    {
        "full_name": "Ana Martinez",
        "years_experience": 4.0,
        "professional_summary": "Machine Learning Engineer focused on NLP and recommendation systems. Experience with PyTorch, TensorFlow, and deploying ML models to production. Published research in computer vision.",
        "contact": {"email": "ana.martinez@example.com", "phone": "+1-408-555-0707", "city": "San Jose", "region": "CA", "country": "US"},
        "skills": [
            {"name": "Python", "level": "Expert", "years": 4.0},
            {"name": "PyTorch", "level": "Advanced", "years": 3.0},
            {"name": "TensorFlow", "level": "Advanced", "years": 3.0},
            {"name": "SQL", "level": "Intermediate", "years": 2.0},
            {"name": "Docker", "level": "Intermediate", "years": 2.0},
            {"name": "FastAPI", "level": "Intermediate", "years": 2.0}
        ],
        "education": [
            {"institution": "Stanford University", "degree": "MS", "field_of_study": "Artificial Intelligence", "graduation_year": 2020}
        ],
        "experience": [
            {"company": "AI Startup", "title": "ML Engineer", "start_date": datetime(2020, 9, 1), "end_date": None, "description": "Building NLP models for search and recommendations"}
        ]
    },
    {
        "full_name": "Robert Johnson",
        "years_experience": 10.0,
        "professional_summary": "Backend Engineer specializing in high-performance systems. Expert in Go, Rust, and low-latency architectures. Optimized critical services to handle 100K+ RPS with sub-10ms latency.",
        "contact": {"email": "rob.johnson@example.com", "phone": "+1-303-555-0808", "city": "Denver", "region": "CO", "country": "US"},
        "skills": [
            {"name": "Go", "level": "Expert", "years": 7.0},
            {"name": "Rust", "level": "Advanced", "years": 4.0},
            {"name": "PostgreSQL", "level": "Expert", "years": 10.0},
            {"name": "Redis", "level": "Expert", "years": 8.0},
            {"name": "Kafka", "level": "Advanced", "years": 5.0},
            {"name": "Docker", "level": "Advanced", "years": 6.0},
            {"name": "System Design", "level": "Advanced", "years": 8.0}
        ],
        "education": [
            {"institution": "University of Colorado", "degree": "BS", "field_of_study": "Computer Science", "graduation_year": 2014}
        ],
        "experience": [
            {"company": "FinTech Inc", "title": "Staff Engineer", "start_date": datetime(2019, 1, 1), "end_date": None, "description": "High-frequency trading systems"},
            {"company": "DataStream", "title": "Senior Engineer", "start_date": datetime(2014, 7, 1), "end_date": datetime(2018, 12, 31), "description": "Real-time data processing"}
        ]
    }
]

# Mock data options for randomization
WORK_AUTHORIZATIONS = ["US Citizen", "Green Card", "H1B", "OPT", "L1", "TN Visa"]
WORK_ARRANGEMENTS = ["Remote", "Hybrid", "On-site"]
RELOCATE_OPTIONS = ["Yes", "No", "Yes - within US", "Yes - anywhere", "Open to discussion"]
ETHNICITIES = ["Asian", "Black or African American", "Hispanic or Latino", "White", "Two or more races", "Prefer not to say"]
DISABILITY_OPTIONS = ["No", "Yes", "Prefer not to say"]
VETERAN_OPTIONS = ["No", "Yes - Active Duty", "Yes - Veteran", "Yes - Reserve", "Prefer not to say"]


def generate_mock_preference(years_exp: float) -> dict:
    """Generate realistic mock preference data based on experience level."""
    # Higher experience = higher salary expectations
    base_salary = 60000 + (years_exp * 8000)
    salary_min = int(base_salary * 0.9)
    salary_max = int(base_salary * 1.3)

    return {
        "work_authorization": random.choice(WORK_AUTHORIZATIONS),
        "work_arrangement": random.choice(WORK_ARRANGEMENTS),
        "willing_to_relocate": random.choice(RELOCATE_OPTIONS),
        "desired_salary_min": salary_min,
        "desired_salary_max": salary_max,
        "salary_currency": "USD",
        "salary_period": "year",
        "availability_start": random.choice(["Immediately", "2 weeks", "1 month", "Negotiable"]),
        "open_to_remote": random.choice([True, False, True, True])  # 75% prefer remote
    }


def generate_mock_demographics() -> dict:
    """Generate mock demographic data for testing queries."""
    return {
        "disability": random.choice(DISABILITY_OPTIONS),
        "ethnicity": random.choice(ETHNICITIES),
        "veteran_status": random.choice(VETERAN_OPTIONS)
    }


async def create_jobs(db):
    """Create job postings in database (skip if already exists)."""

    print("\n" + "="*60)
    print("CREATING JOBS")
    print("="*60)

    # Check which jobs already exist (by title)
    existing_jobs_result = await db.execute(select(Job))
    existing_jobs = existing_jobs_result.scalars().all()
    existing_job_titles = {job.title for job in existing_jobs}

    job_objects = list(existing_jobs)  # Start with existing jobs
    new_jobs_count = 0

    for job_data in DUMMY_JOBS:
        if job_data["title"] in existing_job_titles:
            print(f"   ℹ️  Skipped existing job: {job_data['title']}")
            continue

        try:
            # Create job
            job = Job(
                title=job_data["title"],
                description=job_data["description"],
                department=job_data["department"],
                location=job_data["location"],
                status=job_data["status"],
                required_skills_json=job_data["required_skills_json"],
                must_have_skills_json=job_data["must_have_skills_json"],
                min_years_experience=job_data["min_years_experience"],
                max_years_experience=job_data["max_years_experience"],
                work_arrangement=job_data["work_arrangement"],
                employment_type=job_data["employment_type"]
            )

            db.add(job)
            job_objects.append(job)
            new_jobs_count += 1

        except Exception as e:
            print(f"   ⚠️  Error creating job '{job_data['title']}': {e}")
            continue

    if new_jobs_count > 0:
        await db.commit()

        # Refresh to get IDs for new jobs
        for job in job_objects:
            await db.refresh(job)

        print(f"✅ Created {new_jobs_count} new jobs:")
        for job in job_objects[-new_jobs_count:]:  # Only show new jobs
            print(f"   • {job.title} ({job.location})")
    else:
        print(f"   ℹ️  No new jobs to create (all {len(existing_job_titles)} jobs already exist)")

    print(f"   📊 Total jobs available: {len(job_objects)}")

    return job_objects


async def create_skills(db):
    """Create skill ontology (skip if already exists)."""

    print("\n1️⃣ Creating skills ontology...")

    # Core programming languages
    skills = [
        "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C#",
        "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R",
        # Frontend
        "React", "Angular", "Vue.js", "HTML", "CSS", "Node.js",
        # Backend frameworks
        "FastAPI", "Django", "Flask", "Spring Boot", "Express.js",
        # Databases
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra", "SQL",
        # Cloud & DevOps
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Jenkins", "Bash",
        # Big Data & ML
        "Apache Spark", "Kafka", "PyTorch", "TensorFlow", "Hadoop",
        # Other
        "System Design", "Microservices", "REST API", "GraphQL", "Git"
    ]

    # Check which skills already exist
    existing_skills_result = await db.execute(select(Skill))
    existing_skills = existing_skills_result.scalars().all()
    existing_skill_names = {skill.name for skill in existing_skills}

    skill_objects = {}

    # Add existing skills to skill_objects
    for skill in existing_skills:
        skill_objects[skill.name] = skill

    # Only create skills that don't exist yet
    new_skills_count = 0
    for skill_name in skills:
        if skill_name not in existing_skill_names:
            skill_id = uuid.uuid4()
            skill = Skill(id=skill_id, name=skill_name, parent_skill_id=None)
            db.add(skill)
            skill_objects[skill_name] = skill
            new_skills_count += 1

    if new_skills_count > 0:
        await db.flush()
        print(f"   ✅ Created {new_skills_count} new skills")

    if len(existing_skill_names) > 0:
        print(f"   ℹ️  Skipped {len(existing_skill_names)} existing skills")

    print(f"   📊 Total skills available: {len(skill_objects)}")

    return skill_objects


async def create_candidates(db, skill_objects):
    """Create dummy candidates with full profiles (skip if already exists)."""

    print("\n2️⃣ Creating candidates...")

    # Check which candidates already exist (by full_name)
    existing_candidates_result = await db.execute(select(Candidate))
    existing_candidates = existing_candidates_result.scalars().all()
    existing_candidate_names = {c.full_name for c in existing_candidates}

    candidate_ids = []
    new_candidates_count = 0

    for i, cand_data in enumerate(DUMMY_CANDIDATES, 1):
        if cand_data["full_name"] in existing_candidate_names:
            print(f"   ℹ️  {i}/{len(DUMMY_CANDIDATES)}: {cand_data['full_name']} (already exists)")
            continue

        try:
            # Create candidate
            candidate_id = uuid.uuid4()
            candidate = Candidate(
                id=candidate_id,
                full_name=cand_data["full_name"],
                years_experience=cand_data["years_experience"],
                professional_summary=cand_data["professional_summary"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(candidate)
            candidate_ids.append(candidate_id)

            # Add contact
            contact_data = cand_data["contact"]
            contact = CandidateContact(
                candidate_id=candidate_id,
                email=contact_data["email"],
                phone=contact_data.get("phone"),
                city=contact_data.get("city"),
                region=contact_data.get("region"),
                country=contact_data.get("country")
            )
            db.add(contact)

            # Add preferences (mock data)
            pref_data = generate_mock_preference(cand_data["years_experience"])
            preference = CandidatePreference(
                candidate_id=candidate_id,
                work_authorization=pref_data["work_authorization"],
                work_arrangement=pref_data["work_arrangement"],
                willing_to_relocate=pref_data["willing_to_relocate"],
                desired_salary_min=pref_data["desired_salary_min"],
                desired_salary_max=pref_data["desired_salary_max"],
                salary_currency=pref_data["salary_currency"],
                salary_period=pref_data["salary_period"],
                availability_start=pref_data["availability_start"],
                open_to_remote=pref_data["open_to_remote"]
            )
            db.add(preference)

            # Add demographics (mock data)
            demo_data = generate_mock_demographics()
            demographics = CandidateDemographics(
                candidate_id=candidate_id,
                disability=demo_data["disability"],
                ethnicity=demo_data["ethnicity"],
                veteran_status=demo_data["veteran_status"]
            )
            db.add(demographics)

            # Add skills
            for skill_data in cand_data["skills"]:
                skill_name = skill_data["name"]
                if skill_name in skill_objects:
                    candidate_skill = CandidateSkill(
                        candidate_id=candidate_id,
                        skill_id=skill_objects[skill_name].id,
                        level=skill_data["level"],
                        years=skill_data["years"]
                    )
                    db.add(candidate_skill)

            print(f"   ✅ {i}/{len(DUMMY_CANDIDATES)}: {cand_data['full_name']}")
            new_candidates_count += 1

        except Exception as e:
            print(f"   ❌ Failed to create {cand_data['full_name']}: {str(e)}")
            await db.rollback()
            raise  # Re-raise to stop and show full error

    if new_candidates_count > 0:
        await db.commit()
        print(f"   ✅ Created {new_candidates_count} new candidates with full profiles")

    if len(existing_candidate_names) > 0:
        print(f"   ℹ️  Skipped {len(existing_candidate_names)} existing candidates")

    print(f"   📊 Total candidates available: {new_candidates_count + len(existing_candidate_names)}")

    return candidate_ids


async def populate_qdrant(db):
    """Generate and store embeddings in Qdrant (profile + skills + dummy chunk per candidate)."""

    print("\n3️⃣ Populating Qdrant with embeddings...")

    # Ensure collection exists
    vector_store.create_collection(vector_size=384)
    print("   ✅ Collection ready")

    # Get all candidates
    result = await db.execute(select(Candidate))
    candidates = result.scalars().all()

    for i, candidate in enumerate(candidates, 1):
        try:
            # Get candidate skills
            result = await db.execute(
                select(Skill.name)
                .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
                .where(CandidateSkill.candidate_id == candidate.id)
            )
            skill_names = [name for (name,) in result.all()]

            # 1. Generate profile embedding
            profile_text = f"{candidate.full_name}\n{candidate.professional_summary or 'No summary available'}"
            profile_embedding = await embedding_service.embed_text(profile_text)

            # 2. Generate skills embedding
            skills_text = " ".join(skill_names) if skill_names else "No skills"
            skills_embedding = await embedding_service.embed_text(skills_text)

            # 3. Generate a dummy chunk embedding (using summary as chunk)
            chunk_text = candidate.professional_summary or "No experience details available"
            chunk_embedding = await embedding_service.embed_text(chunk_text)

            # Build all vectors and payloads
            vectors = [profile_embedding, skills_embedding, chunk_embedding]
            payloads = [
                {
                    "candidate_id": str(candidate.id),
                    "kind": "profile",
                    "full_name": candidate.full_name,
                    "text": profile_text[:500],
                    "skills": skill_names,
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "candidate_id": str(candidate.id),
                    "kind": "skills",
                    "skills": skill_names,
                    "skills_count": len(skill_names),
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "candidate_id": str(candidate.id),
                    "kind": "chunk",
                    "chunk_index": 0,
                    "chunk_text": chunk_text[:500],
                    "skills_detected": skill_names,
                    "created_at": datetime.utcnow().isoformat()
                }
            ]

            # Store in Qdrant
            success = vector_store.upsert_vectors(vectors, payloads)

            if success:
                print(f"   ✅ {i}/{len(candidates)}: {candidate.full_name} (profile + skills + 1 chunk)")
            else:
                print(f"   ⚠️  {i}/{len(candidates)}: {candidate.full_name} (upsert failed)")

        except Exception as e:
            print(f"   ❌ {i}/{len(candidates)}: {candidate.full_name} - Error: {e}")

    # Verify
    info = vector_store.get_collection_info()
    print(f"\n   Qdrant collection info:")
    print(f"   • Vectors: {info.get('vectors_count', 0)}")
    print(f"   • Points: {info.get('points_count', 0)}")
    print(f"   • Expected: {len(candidates) * 3} vectors (3 per candidate)")


async def populate_minio(db):
    """Upload resume files to MinIO for candidates (skip if already exists)."""

    print("\n4️⃣ Uploading resumes to MinIO...")

    # Map candidate names to resume file names
    # Only 5 out of 8 candidates have resumes (for testing)
    resume_mapping = {
        "Sarah Chen": "sarah_chen_resume.txt",
        "Michael Rodriguez": "michael_rodriguez_resume.txt",
        "Emily Watson": "emily_watson_resume.txt",
        "Priya Patel": "priya_patel_resume.txt",
        "James Thompson": "james_thompson_resume.txt"
        # David Kim, Ana Martinez, Robert Johnson have no resumes (for testing)
    }

    # Get path to resumes directory (relative to project root)
    # backend/populate_dummy_data.py -> backend/ -> RightStaff/ -> resumes/
    project_root = Path(__file__).parent.parent
    resumes_dir = project_root / "resumes"

    if not resumes_dir.exists():
        print(f"   ⚠️  Resumes directory not found: {resumes_dir}")
        print(f"   💡 Create {resumes_dir} and add resume files")
        return

    # Get all candidates
    result = await db.execute(
        select(Candidate.id, Candidate.full_name)
    )
    candidates = result.all()

    # Check which candidates already have resumes
    existing_resumes_result = await db.execute(select(CandidateResume.candidate_id))
    existing_resume_candidate_ids = {r[0] for r in existing_resumes_result.all()}

    uploaded_count = 0
    skipped_count = 0
    existing_count = 0

    for i, (cand_id, name) in enumerate(candidates, 1):
        try:
            # Check if resume already exists
            if cand_id in existing_resume_candidate_ids:
                print(f"   ℹ️  {i}/{len(candidates)}: {name} (resume already exists)")
                existing_count += 1
                continue

            # Check if this candidate has a resume
            if name not in resume_mapping:
                print(f"   ⏭️  {i}/{len(candidates)}: {name} (no resume - for testing)")
                skipped_count += 1
                continue

            resume_filename = resume_mapping[name]
            resume_path = resumes_dir / resume_filename

            if not resume_path.exists():
                print(f"   ⚠️  {i}/{len(candidates)}: {name} - Resume file not found: {resume_filename}")
                continue

            # Read resume file
            with open(resume_path, 'rb') as f:
                resume_data = f.read()

            # Upload to MinIO
            object_name = f"resumes/{cand_id}/{resume_filename}"
            s3_url = await s3_client.upload_file(
                file_data=resume_data,
                object_name=object_name,
                content_type="text/plain"
            )

            # Create database record
            resume_record = CandidateResume(
                id=uuid.uuid4(),
                candidate_id=cand_id,
                s3_url=s3_url,
                file_type="text/plain",
                is_latest=True,
                uploaded_at=datetime.utcnow()
            )
            db.add(resume_record)

            print(f"   ✅ {i}/{len(candidates)}: {name} - Uploaded {len(resume_data)} bytes")
            uploaded_count += 1

        except Exception as e:
            print(f"   ❌ {i}/{len(candidates)}: {name} - Error: {e}")

    if uploaded_count > 0:
        await db.commit()

    print(f"\n   Summary:")
    print(f"   • Uploaded: {uploaded_count} new resumes")
    print(f"   • Existing: {existing_count} resumes already uploaded")
    print(f"   • Skipped: {skipped_count} candidates (for testing)")


async def create_job_embeddings(db):
    """Generate and store embeddings for all jobs."""

    print("\n" + "="*60)
    print("CREATING JOB EMBEDDINGS")
    print("="*60)

    from app.services.job_embeddings import generate_job_embeddings

    # Get all jobs
    jobs_result = await db.execute(select(Job))
    jobs = jobs_result.scalars().all()

    if not jobs:
        print("⚠️  No jobs found - skipping job embeddings")
        return

    embeddings_created = 0

    for job in jobs:
        try:
            # Generate embeddings
            embeddings = await generate_job_embeddings(
                job_id=str(job.id),
                title=job.title,
                description=job.description or "",
                required_skills=job.required_skills_json or []
            )

            # Store in Qdrant jobs_v1 collection
            points = [
                {
                    "id": f"{job.id}_profile",
                    "vector": embeddings["profile_vector"],
                    "payload": {
                        "job_id": str(job.id),
                        "type": "profile",
                        "title": job.title,
                        "created_at": datetime.utcnow().isoformat()
                    }
                },
                {
                    "id": f"{job.id}_skills",
                    "vector": embeddings["skills_vector"],
                    "payload": {
                        "job_id": str(job.id),
                        "type": "skills",
                        "skills": job.required_skills_json or [],
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
            ]

            await vector_store.upsert_points(points, collection_name="jobs_v1")
            embeddings_created += 1

            print(f"  ✅ {job.title}: embeddings created")

        except Exception as e:
            print(f"  ⚠️  {job.title}: failed - {e}")
            continue

    print(f"✅ Created embeddings for {embeddings_created}/{len(jobs)} jobs")


async def create_applications(db):
    """Create job applications for testing (skip if already exists)."""

    print("\n" + "="*60)
    print("CREATING JOB APPLICATIONS")
    print("="*60)

    # Get first 3 jobs and first 10 candidates for demo
    jobs_result = await db.execute(select(Job).limit(3))
    jobs = jobs_result.scalars().all()

    candidates_result = await db.execute(select(Candidate).limit(10))
    candidates = candidates_result.scalars().all()

    if not jobs:
        print("⚠️  No jobs found - skipping application creation")
        return
    elif not candidates:
        print("⚠️  No candidates found - skipping application creation")
        return

    # Get existing applications to avoid duplicates
    existing_applications_result = await db.execute(select(Application))
    existing_applications = existing_applications_result.scalars().all()
    existing_pairs = {(app.candidate_id, app.job_id) for app in existing_applications}

    applications_created = 0
    applications_skipped = 0

    # Create applications: first 10 candidates apply to first 3 jobs
    for job in jobs:
        for candidate in candidates:
            try:
                # Check if application already exists
                if (candidate.id, job.id) in existing_pairs:
                    applications_skipped += 1
                    continue

                # Create application
                application = Application(
                    candidate_id=candidate.id,
                    job_id=job.id,
                    status=ApplicationStatus.applied
                )
                db.add(application)
                applications_created += 1
            except Exception as e:
                print(f"⚠️  Failed to create application: {e}")
                continue

    if applications_created > 0:
        await db.commit()

    print(f"✅ Applications summary:")
    print(f"   • Created: {applications_created} new applications")
    print(f"   • Skipped: {applications_skipped} existing applications")
    print(f"   • Total jobs: {len(jobs)}")
    print(f"   • Total candidates: {len(candidates)}")


async def populate_all():
    """Populate all systems with dummy data."""

    print("\n" + "="*70)
    print("  POPULATING DUMMY DATA")
    print("="*70)

    async with AsyncSessionLocal() as db:
        # Create jobs
        job_objects = await create_jobs(db)

        # Create skills
        skill_objects = await create_skills(db)

        # Create candidates
        candidate_ids = await create_candidates(db, skill_objects)

        # Populate Qdrant
        await populate_qdrant(db)

        # Populate MinIO
        await populate_minio(db)

        # Create job embeddings
        await create_job_embeddings(db)

        # Create applications
        await create_applications(db)

    # Summary
    print("\n" + "="*70)
    print("✅ Dummy data populated successfully!")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"   • Jobs: {len(job_objects)}")
    print(f"   • Candidates: {len(DUMMY_CANDIDATES)}")
    print(f"   • Skills: {len(skill_objects)}")
    print(f"   • Candidate Vectors in Qdrant: {len(DUMMY_CANDIDATES)}")
    print(f"   • Job Embeddings in Qdrant: {len(job_objects) * 2} (profile + skills)")
    print(f"   • Resumes in MinIO: 5 (3 candidates without resumes for testing)")
    print("\n💡 Next steps:")
    print("   1. Check data: python check_database.py")
    print("   2. Run diagnostic: python diagnose_all.py")
    print("   3. Test ranking: python test_day4_e2e_adaptive.py")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(populate_all())
