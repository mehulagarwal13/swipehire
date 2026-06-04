"""
Seed 100 realistic Indian tech jobs into the database.
Run: python seed_jobs.py

Uses Faker with Indian locale + manually curated job templates for realism.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings
from models.job import Job

fake = Faker("en_IN")
Faker.seed(42)

# ─── Data pools ───────────────────────────────────────────────────────────────

COMPANIES = [
    "Infosys", "TCS", "Wipro", "HCL Technologies", "Tech Mahindra",
    "Razorpay", "Zepto", "Swiggy", "Zomato", "Meesho",
    "PhonePe", "Groww", "CRED", "Postman", "BrowserStack",
    "Freshworks", "Zoho", "MakeMyTrip", "OLA", "Byju's",
    "Unacademy", "Vedantu", "Nykaa", "Mamaearth", "ShareChat",
    "Dream11", "MPL", "Games24x7", "Flipkart", "Amazon India",
    "Microsoft India", "Google India", "Adobe India", "SAP Labs",
    "Oracle India", "IBM India", "Accenture", "Capgemini", "Cognizant",
]

ROLES = [
    ("Software Development Engineer", ["JavaScript", "TypeScript", "React", "Node.js"], "Engineering"),
    ("Backend Engineer", ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"], "Engineering"),
    ("Frontend Developer", ["React", "Next.js", "TypeScript", "TailwindCSS", "GraphQL"], "Engineering"),
    ("Full Stack Developer", ["React", "Node.js", "MongoDB", "Express", "AWS"], "Engineering"),
    ("Data Engineer", ["Python", "Apache Spark", "Airflow", "AWS", "SQL"], "Data"),
    ("Machine Learning Engineer", ["Python", "TensorFlow", "PyTorch", "Scikit-learn", "MLflow"], "AI/ML"),
    ("DevOps Engineer", ["Docker", "Kubernetes", "AWS", "Terraform", "CI/CD"], "DevOps"),
    ("Android Developer", ["Kotlin", "Android SDK", "Jetpack Compose", "Retrofit"], "Mobile"),
    ("iOS Developer", ["Swift", "SwiftUI", "Xcode", "CoreData", "Combine"], "Mobile"),
    ("React Native Developer", ["React Native", "TypeScript", "Redux", "Firebase"], "Mobile"),
    ("Data Scientist", ["Python", "Pandas", "Scikit-learn", "SQL", "Tableau"], "Data"),
    ("Product Manager", ["Product Strategy", "Agile", "SQL", "Figma", "Analytics"], "Product"),
    ("UI/UX Designer", ["Figma", "Adobe XD", "Prototyping", "User Research"], "Design"),
    ("QA Engineer", ["Selenium", "Cypress", "Python", "Jest", "API Testing"], "QA"),
    ("Security Engineer", ["OWASP", "Penetration Testing", "Python", "AWS Security"], "Security"),
    ("Cloud Architect", ["AWS", "GCP", "Azure", "Terraform", "Kubernetes"], "Cloud"),
    ("Blockchain Developer", ["Solidity", "Web3.js", "Ethereum", "Hardhat"], "Web3"),
    ("Site Reliability Engineer", ["Linux", "Python", "Prometheus", "Grafana", "Kubernetes"], "SRE"),
]

LOCATIONS = [
    "Bangalore", "Mumbai", "Delhi NCR", "Hyderabad", "Pune",
    "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Remote",
]

JOB_TYPES = ["full-time", "full-time", "full-time", "internship", "contract"]

SOURCES = ["seed", "seed", "naukri", "linkedin"]


def _random_salary(exp_min: float) -> tuple[float, float]:
    base = max(3.0, exp_min * 4)
    salary_min = round(base + random.uniform(-1, 1), 1)
    salary_max = round(salary_min + random.uniform(3, 8), 1)
    return salary_min, salary_max


def _random_exp() -> tuple[float, float]:
    exp_min = random.choice([0, 0, 1, 2, 3, 5])
    exp_max = exp_min + random.choice([1, 2, 3])
    return float(exp_min), float(exp_max)


def _make_description(role: str, company: str, skills: list[str]) -> str:
    return (
        f"{company} is looking for a talented {role} to join our growing engineering team. "
        f"You will work on cutting-edge products used by millions of Indians. "
        f"\n\nKey Responsibilities:\n"
        f"• Design, build, and maintain efficient, reusable, and reliable code\n"
        f"• Collaborate with cross-functional teams including Product, Design, and Data\n"
        f"• Participate in code reviews and mentor junior engineers\n"
        f"• Contribute to system design and architecture decisions\n"
        f"\nRequired Skills: {', '.join(skills)}\n"
        f"\nWhat we offer:\n"
        f"• Competitive compensation and ESOPs\n"
        f"• Flexible work arrangements\n"
        f"• Learning & development budget\n"
        f"• Health insurance for self + family"
    )


async def seed(db: AsyncSession) -> None:
    jobs = []
    for i in range(100):
        role_data = random.choice(ROLES)
        title, skills, industry = role_data

        company = random.choice(COMPANIES)
        location = random.choice(LOCATIONS)
        is_remote = location == "Remote" or random.random() < 0.2
        job_type = random.choice(JOB_TYPES)
        exp_min, exp_max = _random_exp()
        sal_min, sal_max = _random_salary(exp_min)
        source = random.choice(SOURCES)
        posted_at = datetime.utcnow() - timedelta(days=random.randint(0, 30))

        job = Job(
            external_id=f"seed_{i:04d}",
            source=source,
            title=title,
            company=company,
            location=location if not is_remote else "Remote",
            is_remote=is_remote,
            salary_min_lpa=sal_min,
            salary_max_lpa=sal_max,
            experience_min=exp_min,
            experience_max=exp_max,
            skills_required=skills + random.sample(
                ["Git", "Agile", "REST APIs", "Microservices", "Linux"], k=random.randint(0, 2)
            ),
            description=_make_description(title, company, skills),
            apply_url=f"https://careers.{company.lower().replace(' ','')}.com/jobs/{i}",
            job_type=job_type,
            industry=industry,
            posted_at=posted_at,
        )
        jobs.append(job)

    db.add_all(jobs)
    await db.commit()
    print(f"✅ Seeded {len(jobs)} jobs successfully")


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
