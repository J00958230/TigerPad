"""
Overall function:
This file prepares TigerPad's development database with repeatable reference
data. It verifies the environment, connects to MySQL, and inserts only
missing roles, industries, career paths, skills, skill mappings, and JSU
career resources.

TigerPad serves every Jackson State University student, so the seeded data
covers business, education, healthcare, science, liberal arts, communication,
public service, engineering, technology, and other disciplines.

Team ownership:
- Jay: Project Manager
- Cell: Cybersecurity Lead
- Tim: Database Lead
- Ash: Software Engineer Lead
- Mohammad: Programming Lead

Development accounts are not created until authentication and password
security are finalized.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from TP_App import models
from TP_App.config import settings
from TP_App.database.base import Base
from TP_App.database.connection import (
    SessionLocal,
    check_database_connection,
)
from TP_App.models import (
    CareerPath,
    CareerPathSkill,
    Industry,
    Resource,
    Role,
    Skill,
)


# Importing TP_App.models registers all model classes with SQLAlchemy metadata.
_REGISTERED_MODELS = models


ROLE_ROWS: tuple[dict[str, Any], ...] = (
    {
        "name": "student",
        "description": (
            "JSU student using TigerPad career-readiness features."
        ),
    },
    {
        "name": "faculty",
        "description": (
            "JSU faculty or staff member who can support students."
        ),
    },
    {
        "name": "admin",
        "description": (
            "TigerPad administrator responsible for website management."
        ),
    },
)


INDUSTRY_ROWS: tuple[dict[str, Any], ...] = (
    {
        "name": "Technology",
        "industry_code": "TECH",
        "description": (
            "Technology, information systems, software, and digital services."
        ),
    },
    {
        "name": "Healthcare",
        "industry_code": "HEALTH",
        "description": (
            "Clinical, administrative, and support careers in healthcare."
        ),
    },
    {
        "name": "Education",
        "industry_code": "EDUCATION",
        "description": (
            "Teaching, learning design, student support, and leadership."
        ),
    },
    {
        "name": "Business",
        "industry_code": "BUSINESS",
        "description": (
            "Operations, management, entrepreneurship, and organizations."
        ),
    },
    {
        "name": "Finance and Accounting",
        "industry_code": "FINANCE",
        "description": (
            "Accounting, budgeting, financial analysis, and financial services."
        ),
    },
    {
        "name": "Engineering",
        "industry_code": "ENGINEERING",
        "description": (
            "Engineering design, infrastructure, systems, and problem solving."
        ),
    },
    {
        "name": "Science",
        "industry_code": "SCIENCE",
        "description": (
            "Scientific research, laboratory work, analysis, and discovery."
        ),
    },
    {
        "name": "Government and Public Administration",
        "industry_code": "GOVERNMENT",
        "description": (
            "Public programs, policy, government operations, and civic services."
        ),
    },
    {
        "name": "Public Safety",
        "industry_code": "PUBLIC_SAFETY",
        "description": (
            "Criminal justice, emergency services, corrections, and safety."
        ),
    },
    {
        "name": "Arts and Design",
        "industry_code": "ARTS",
        "description": (
            "Visual arts, design, creative production, and artistic work."
        ),
    },
    {
        "name": "Media and Communications",
        "industry_code": "MEDIA",
        "description": (
            "Journalism, public relations, media, and communications."
        ),
    },
    {
        "name": "Community and Social Services",
        "industry_code": "COMMUNITY",
        "description": (
            "Social work, counseling support, advocacy, and community service."
        ),
    },
    {
        "name": "Public Health",
        "industry_code": "PUBLIC_HEALTH",
        "description": (
            "Population health, prevention, health education, and policy."
        ),
    },
    {
        "name": "Hospitality and Tourism",
        "industry_code": "HOSPITALITY",
        "description": (
            "Hospitality operations, events, tourism, and guest services."
        ),
    },
    {
        "name": "Human Resources",
        "industry_code": "HUMAN_RESOURCES",
        "description": (
            "Recruiting, employee development, and workplace relations."
        ),
    },
    {
        "name": "Legal Services",
        "industry_code": "LEGAL",
        "description": (
            "Legal support, compliance, research, and justice-related work."
        ),
    },
    {
        "name": "Nonprofit and Community Development",
        "industry_code": "NONPROFIT",
        "description": (
            "Mission-driven organizations, fundraising, programs, and advocacy."
        ),
    },
    {
        "name": "Sports and Recreation",
        "industry_code": "SPORTS",
        "description": (
            "Athletics, recreation, wellness, and sports operations."
        ),
    },
    {
        "name": "Environment and Sustainability",
        "industry_code": "ENVIRONMENT",
        "description": (
            "Environmental programs, conservation, and sustainability."
        ),
    },
)


CAREER_PATH_ROWS: tuple[dict[str, Any], ...] = (
    {
        "industry_code": "TECH",
        "name": "Cybersecurity Analyst",
        "career_path_code": "CYBERSECURITY_ANALYST",
        "description": (
            "Protects systems, investigates security events, identifies "
            "vulnerabilities, and helps reduce cyber risk."
        ),
        "typical_education_level": (
            "Bachelor degree or relevant certifications"
        ),
    },
    {
        "industry_code": "TECH",
        "name": "Data Analyst",
        "career_path_code": "DATA_ANALYST",
        "description": (
            "Transforms information into findings that support organizational "
            "decisions."
        ),
        "typical_education_level": (
            "Bachelor degree or equivalent experience"
        ),
    },
    {
        "industry_code": "TECH",
        "name": "IT Support Specialist",
        "career_path_code": "IT_SUPPORT_SPECIALIST",
        "description": (
            "Supports users, devices, networks, applications, and technology "
            "operations."
        ),
        "typical_education_level": (
            "Associate or bachelor degree; certifications"
        ),
    },
    {
        "industry_code": "HEALTH",
        "name": "Healthcare Administrator",
        "career_path_code": "HEALTHCARE_ADMINISTRATOR",
        "description": (
            "Coordinates healthcare operations, employees, records, budgets, "
            "and services."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "PUBLIC_HEALTH",
        "name": "Public Health Analyst",
        "career_path_code": "PUBLIC_HEALTH_ANALYST",
        "description": (
            "Examines population-health information and supports prevention "
            "programs and policy."
        ),
        "typical_education_level": (
            "Bachelor degree; graduate preferred"
        ),
    },
    {
        "industry_code": "EDUCATION",
        "name": "Teacher",
        "career_path_code": "TEACHER",
        "description": (
            "Plans lessons, teaches students, evaluates learning, and supports "
            "student development."
        ),
        "typical_education_level": (
            "Bachelor degree and teaching license"
        ),
    },
    {
        "industry_code": "EDUCATION",
        "name": "Instructional Designer",
        "career_path_code": "INSTRUCTIONAL_DESIGNER",
        "description": (
            "Designs learning materials, activities, assessments, and training "
            "experiences."
        ),
        "typical_education_level": (
            "Bachelor degree or relevant experience"
        ),
    },
    {
        "industry_code": "BUSINESS",
        "name": "Business Operations Analyst",
        "career_path_code": "BUSINESS_OPERATIONS_ANALYST",
        "description": (
            "Studies business processes and recommends ways to improve "
            "performance and efficiency."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "FINANCE",
        "name": "Accountant",
        "career_path_code": "ACCOUNTANT",
        "description": (
            "Prepares financial records, reviews transactions, and supports "
            "financial compliance."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "FINANCE",
        "name": "Financial Analyst",
        "career_path_code": "FINANCIAL_ANALYST",
        "description": (
            "Evaluates financial information, budgets, forecasts, and business "
            "performance."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "ENGINEERING",
        "name": "Civil Engineer",
        "career_path_code": "CIVIL_ENGINEER",
        "description": (
            "Designs and evaluates infrastructure, transportation, water, and "
            "construction systems."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "SCIENCE",
        "name": "Research Scientist",
        "career_path_code": "RESEARCH_SCIENTIST",
        "description": (
            "Plans experiments, analyzes scientific information, and documents "
            "research results."
        ),
        "typical_education_level": (
            "Bachelor degree; graduate preferred"
        ),
    },
    {
        "industry_code": "GOVERNMENT",
        "name": "Public Administrator",
        "career_path_code": "PUBLIC_ADMINISTRATOR",
        "description": (
            "Supports public programs, evaluates policy, and manages government "
            "operations."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "PUBLIC_SAFETY",
        "name": "Criminal Justice Specialist",
        "career_path_code": "CRIMINAL_JUSTICE_SPECIALIST",
        "description": (
            "Supports law enforcement, courts, corrections, investigations, "
            "or public safety programs."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "ARTS",
        "name": "Creative Designer",
        "career_path_code": "CREATIVE_DESIGNER",
        "description": (
            "Creates visual concepts and artistic materials for organizations, "
            "media, products, or campaigns."
        ),
        "typical_education_level": (
            "Bachelor degree or professional portfolio"
        ),
    },
    {
        "industry_code": "MEDIA",
        "name": "Communications Specialist",
        "career_path_code": "COMMUNICATIONS_SPECIALIST",
        "description": (
            "Creates written and digital content and communicates with "
            "audiences and media organizations."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "COMMUNITY",
        "name": "Social Worker",
        "career_path_code": "SOCIAL_WORKER",
        "description": (
            "Connects individuals and families with services and supports "
            "community well-being."
        ),
        "typical_education_level": (
            "Bachelor degree; licensure varies"
        ),
    },
    {
        "industry_code": "HOSPITALITY",
        "name": "Hospitality Operations Coordinator",
        "career_path_code": "HOSPITALITY_OPERATIONS_COORDINATOR",
        "description": (
            "Coordinates guest services, events, schedules, vendors, and "
            "hospitality operations."
        ),
        "typical_education_level": (
            "Bachelor degree or relevant experience"
        ),
    },
    {
        "industry_code": "HUMAN_RESOURCES",
        "name": "Human Resources Specialist",
        "career_path_code": "HUMAN_RESOURCES_SPECIALIST",
        "description": (
            "Supports recruiting, onboarding, employee relations, records, "
            "and workplace programs."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "LEGAL",
        "name": "Legal Services Coordinator",
        "career_path_code": "LEGAL_SERVICES_COORDINATOR",
        "description": (
            "Coordinates legal documents, case information, deadlines, "
            "clients, and office operations."
        ),
        "typical_education_level": (
            "Bachelor degree or paralegal education"
        ),
    },
    {
        "industry_code": "NONPROFIT",
        "name": "Nonprofit Program Coordinator",
        "career_path_code": "NONPROFIT_PROGRAM_COORDINATOR",
        "description": (
            "Plans mission-driven programs, coordinates partners, and tracks "
            "community outcomes."
        ),
        "typical_education_level": "Bachelor degree",
    },
    {
        "industry_code": "SPORTS",
        "name": "Sports and Recreation Coordinator",
        "career_path_code": "SPORTS_RECREATION_COORDINATOR",
        "description": (
            "Plans athletics, recreation, wellness, events, schedules, and "
            "participant services."
        ),
        "typical_education_level": (
            "Bachelor degree or relevant experience"
        ),
    },
    {
        "industry_code": "ENVIRONMENT",
        "name": "Environmental Program Specialist",
        "career_path_code": "ENVIRONMENTAL_PROGRAM_SPECIALIST",
        "description": (
            "Supports environmental compliance, conservation, sustainability, "
            "and outreach programs."
        ),
        "typical_education_level": "Bachelor degree",
    },
)


SKILL_ROWS: tuple[dict[str, Any], ...] = (
    {
        "name": "Written Communication",
        "skill_code": "WRITTEN_COMMUNICATION",
        "category": "communication",
        "description": "Communicates ideas clearly in professional writing.",
    },
    {
        "name": "Public Speaking",
        "skill_code": "PUBLIC_SPEAKING",
        "category": "communication",
        "description": "Presents information clearly to individuals and groups.",
    },
    {
        "name": "Active Listening",
        "skill_code": "ACTIVE_LISTENING",
        "category": "communication",
        "description": "Listens carefully and confirms understanding.",
    },
    {
        "name": "Presentation Design",
        "skill_code": "PRESENTATION_DESIGN",
        "category": "communication",
        "description": "Organizes visual and spoken information effectively.",
    },
    {
        "name": "Teamwork",
        "skill_code": "TEAMWORK",
        "category": "workplace",
        "description": "Works productively with people in different roles.",
    },
    {
        "name": "Leadership",
        "skill_code": "LEADERSHIP",
        "category": "workplace",
        "description": "Guides people, decisions, and tasks toward shared goals.",
    },
    {
        "name": "Time Management",
        "skill_code": "TIME_MANAGEMENT",
        "category": "workplace",
        "description": "Plans priorities and completes work on time.",
    },
    {
        "name": "Problem Solving",
        "skill_code": "PROBLEM_SOLVING",
        "category": "workplace",
        "description": "Defines problems and develops practical solutions.",
    },
    {
        "name": "Critical Thinking",
        "skill_code": "CRITICAL_THINKING",
        "category": "workplace",
        "description": "Evaluates evidence and alternatives before deciding.",
    },
    {
        "name": "Project Management",
        "skill_code": "PROJECT_MANAGEMENT",
        "category": "workplace",
        "description": "Plans, coordinates, tracks, and completes projects.",
    },
    {
        "name": "Conflict Resolution",
        "skill_code": "CONFLICT_RESOLUTION",
        "category": "workplace",
        "description": "Addresses disagreements respectfully.",
    },
    {
        "name": "Adaptability",
        "skill_code": "ADAPTABILITY",
        "category": "workplace",
        "description": "Adjusts when priorities or circumstances change.",
    },
    {
        "name": "Accounting",
        "skill_code": "ACCOUNTING",
        "category": "business",
        "description": "Records and interprets financial transactions.",
    },
    {
        "name": "Budgeting",
        "skill_code": "BUDGETING",
        "category": "business",
        "description": "Plans and monitors financial resources.",
    },
    {
        "name": "Business Analysis",
        "skill_code": "BUSINESS_ANALYSIS",
        "category": "business",
        "description": "Evaluates processes and supports business decisions.",
    },
    {
        "name": "Marketing",
        "skill_code": "MARKETING",
        "category": "business",
        "description": "Communicates value to intended audiences.",
    },
    {
        "name": "Customer Service",
        "skill_code": "CUSTOMER_SERVICE",
        "category": "business",
        "description": "Responds to customer needs professionally.",
    },
    {
        "name": "Entrepreneurship",
        "skill_code": "ENTREPRENEURSHIP",
        "category": "business",
        "description": "Develops opportunities into sustainable ventures.",
    },
    {
        "name": "Teaching",
        "skill_code": "TEACHING",
        "category": "education",
        "description": "Explains concepts through structured instruction.",
    },
    {
        "name": "Lesson Planning",
        "skill_code": "LESSON_PLANNING",
        "category": "education",
        "description": "Creates objectives, activities, and assessments.",
    },
    {
        "name": "Classroom Management",
        "skill_code": "CLASSROOM_MANAGEMENT",
        "category": "education",
        "description": "Maintains a productive learning environment.",
    },
    {
        "name": "Mentoring",
        "skill_code": "MENTORING",
        "category": "education",
        "description": "Supports another person's growth and learning.",
    },
    {
        "name": "Patient Care",
        "skill_code": "PATIENT_CARE",
        "category": "healthcare",
        "description": "Provides safe and respectful patient support.",
    },
    {
        "name": "Health Education",
        "skill_code": "HEALTH_EDUCATION",
        "category": "healthcare",
        "description": "Communicates information for informed health decisions.",
    },
    {
        "name": "Community Outreach",
        "skill_code": "COMMUNITY_OUTREACH",
        "category": "community",
        "description": "Connects communities with helpful services.",
    },
    {
        "name": "Case Management",
        "skill_code": "CASE_MANAGEMENT",
        "category": "community",
        "description": "Coordinates services, records, and follow-up.",
    },
    {
        "name": "Counseling Support",
        "skill_code": "COUNSELING_SUPPORT",
        "category": "community",
        "description": "Uses supportive communication appropriately.",
    },
    {
        "name": "Laboratory Research",
        "skill_code": "LABORATORY_RESEARCH",
        "category": "science",
        "description": "Performs organized laboratory procedures.",
    },
    {
        "name": "Scientific Writing",
        "skill_code": "SCIENTIFIC_WRITING",
        "category": "science",
        "description": "Communicates methods, evidence, and conclusions.",
    },
    {
        "name": "Data Collection",
        "skill_code": "DATA_COLLECTION",
        "category": "science",
        "description": "Collects information accurately and consistently.",
    },
    {
        "name": "Safety Procedures",
        "skill_code": "SAFETY_PROCEDURES",
        "category": "science",
        "description": "Follows procedures that reduce hazards.",
    },
    {
        "name": "Technical Drawing",
        "skill_code": "TECHNICAL_DRAWING",
        "category": "engineering",
        "description": "Communicates technical designs clearly.",
    },
    {
        "name": "Environmental Assessment",
        "skill_code": "ENVIRONMENTAL_ASSESSMENT",
        "category": "environment",
        "description": "Evaluates environmental conditions and risks.",
    },
    {
        "name": "Graphic Design",
        "skill_code": "GRAPHIC_DESIGN",
        "category": "arts",
        "description": "Creates visual layouts and designs.",
    },
    {
        "name": "Creative Writing",
        "skill_code": "CREATIVE_WRITING",
        "category": "arts",
        "description": "Creates original written work using language and voice.",
    },
    {
        "name": "Photography",
        "skill_code": "PHOTOGRAPHY",
        "category": "arts",
        "description": "Creates and edits photographs.",
    },
    {
        "name": "Video Production",
        "skill_code": "VIDEO_PRODUCTION",
        "category": "media",
        "description": "Plans, records, edits, and publishes video.",
    },
    {
        "name": "Content Creation",
        "skill_code": "CONTENT_CREATION",
        "category": "media",
        "description": "Develops useful written, visual, or digital content.",
    },
    {
        "name": "Policy Analysis",
        "skill_code": "POLICY_ANALYSIS",
        "category": "public_service",
        "description": "Examines policy choices and implementation concerns.",
    },
    {
        "name": "Legal Research",
        "skill_code": "LEGAL_RESEARCH",
        "category": "legal",
        "description": "Finds and summarizes relevant legal information.",
    },
    {
        "name": "Public Administration",
        "skill_code": "PUBLIC_ADMINISTRATION",
        "category": "public_service",
        "description": "Supports public programs and operations.",
    },
    {
        "name": "Social Research",
        "skill_code": "SOCIAL_RESEARCH",
        "category": "social_science",
        "description": "Studies people, communities, and social information.",
    },
    {
        "name": "Computer Literacy",
        "skill_code": "COMPUTER_LITERACY",
        "category": "technology",
        "description": "Uses common computer systems and applications.",
    },
    {
        "name": "Microsoft Office",
        "skill_code": "MICROSOFT_OFFICE",
        "category": "technology",
        "description": "Uses common office productivity applications.",
    },
    {
        "name": "Data Analysis",
        "skill_code": "DATA_ANALYSIS",
        "category": "technology",
        "description": "Cleans, examines, and communicates data patterns.",
    },
    {
        "name": "Python",
        "skill_code": "PYTHON",
        "category": "technology",
        "description": "Uses Python for automation, analysis, or applications.",
    },
    {
        "name": "JavaScript",
        "skill_code": "JAVASCRIPT",
        "category": "technology",
        "description": "Uses JavaScript for interactive web features.",
    },
    {
        "name": "SQL",
        "skill_code": "SQL",
        "category": "technology",
        "description": "Queries and manages relational data.",
    },
    {
        "name": "Cybersecurity",
        "skill_code": "CYBERSECURITY",
        "category": "technology",
        "description": "Protects systems, information, and users.",
    },
    {
        "name": "Git",
        "skill_code": "GIT",
        "category": "technology",
        "description": "Tracks and collaborates on software changes.",
    },
    {
        "name": "Resume Writing",
        "skill_code": "RESUME_WRITING",
        "category": "career_preparation",
        "description": "Presents education, skills, and accomplishments professionally.",
    },
    {
        "name": "Interviewing",
        "skill_code": "INTERVIEWING",
        "category": "career_preparation",
        "description": "Prepares for employment interviews.",
    },
    {
        "name": "Networking",
        "skill_code": "NETWORKING",
        "category": "career_preparation",
        "description": "Builds professional relationships.",
    },
    {
        "name": "Career Planning",
        "skill_code": "CAREER_PLANNING",
        "category": "career_preparation",
        "description": "Sets career goals and development steps.",
    },
)


CAREER_PATH_SKILL_ROWS: dict[
    str,
    tuple[tuple[str, int, int, int, str], ...],
] = {
    "CYBERSECURITY_ANALYST": (
        (
            "CYBERSECURITY",
            5,
            4,
            1,
            "Protects systems and investigates security events.",
        ),
        (
            "CRITICAL_THINKING",
            4,
            4,
            1,
            "Evaluates alerts, evidence, and risk.",
        ),
        (
            "PROBLEM_SOLVING",
            4,
            4,
            1,
            "Supports investigation and remediation.",
        ),
        (
            "WRITTEN_COMMUNICATION",
            3,
            3,
            0,
            "Supports reports and documentation.",
        ),
    ),
    "DATA_ANALYST": (
        (
            "DATA_ANALYSIS",
            5,
            4,
            1,
            "Examines information and communicates findings.",
        ),
        (
            "SQL",
            4,
            3,
            0,
            "Retrieves and organizes relational data.",
        ),
        (
            "CRITICAL_THINKING",
            4,
            4,
            1,
            "Supports accurate interpretation of evidence.",
        ),
        (
            "WRITTEN_COMMUNICATION",
            3,
            3,
            0,
            "Explains findings to decision makers.",
        ),
    ),
    "TEACHER": (
        (
            "TEACHING",
            5,
            4,
            1,
            "Plans and delivers instruction.",
        ),
        (
            "LESSON_PLANNING",
            5,
            4,
            1,
            "Creates organized learning experiences.",
        ),
        (
            "CLASSROOM_MANAGEMENT",
            5,
            4,
            1,
            "Supports a productive classroom.",
        ),
        (
            "ACTIVE_LISTENING",
            3,
            3,
            0,
            "Helps identify learner needs.",
        ),
    ),
    "HEALTHCARE_ADMINISTRATOR": (
        (
            "PROJECT_MANAGEMENT",
            4,
            3,
            0,
            "Supports coordinated healthcare operations.",
        ),
        (
            "WRITTEN_COMMUNICATION",
            4,
            4,
            1,
            "Supports records and policies.",
        ),
        (
            "PROBLEM_SOLVING",
            4,
            4,
            1,
            "Addresses operational challenges.",
        ),
        (
            "MICROSOFT_OFFICE",
            3,
            3,
            0,
            "Supports administrative workflows.",
        ),
    ),
    "BUSINESS_OPERATIONS_ANALYST": (
        (
            "BUSINESS_ANALYSIS",
            5,
            4,
            1,
            "Evaluates processes and performance.",
        ),
        (
            "DATA_ANALYSIS",
            4,
            3,
            0,
            "Supports evidence-based recommendations.",
        ),
        (
            "PROBLEM_SOLVING",
            4,
            4,
            1,
            "Supports process improvement.",
        ),
        (
            "PRESENTATION_DESIGN",
            3,
            3,
            0,
            "Communicates recommendations.",
        ),
    ),
    "ACCOUNTANT": (
        (
            "ACCOUNTING",
            5,
            4,
            1,
            "Supports financial records and reporting.",
        ),
        (
            "BUDGETING",
            4,
            3,
            0,
            "Supports financial planning.",
        ),
        (
            "MICROSOFT_OFFICE",
            3,
            3,
            0,
            "Supports spreadsheets and office workflows.",
        ),
        (
            "CRITICAL_THINKING",
            4,
            4,
            1,
            "Supports financial review.",
        ),
    ),
    "CIVIL_ENGINEER": (
        (
            "PROBLEM_SOLVING",
            5,
            4,
            1,
            "Supports infrastructure challenges.",
        ),
        (
            "CRITICAL_THINKING",
            4,
            4,
            1,
            "Evaluates constraints and evidence.",
        ),
        (
            "TECHNICAL_DRAWING",
            4,
            3,
            0,
            "Communicates technical designs.",
        ),
        (
            "PROJECT_MANAGEMENT",
            3,
            3,
            0,
            "Supports engineering projects.",
        ),
    ),
    "RESEARCH_SCIENTIST": (
        (
            "LABORATORY_RESEARCH",
            5,
            4,
            1,
            "Supports scientific investigation.",
        ),
        (
            "DATA_COLLECTION",
            5,
            4,
            1,
            "Supports accurate measurements.",
        ),
        (
            "SCIENTIFIC_WRITING",
            4,
            4,
            1,
            "Documents research results.",
        ),
        (
            "CRITICAL_THINKING",
            4,
            4,
            1,
            "Supports interpretation of evidence.",
        ),
    ),
    "COMMUNICATIONS_SPECIALIST": (
        (
            "WRITTEN_COMMUNICATION",
            5,
            4,
            1,
            "Supports communication and content.",
        ),
        (
            "CONTENT_CREATION",
            4,
            3,
            0,
            "Supports digital communication products.",
        ),
        (
            "PUBLIC_SPEAKING",
            3,
            3,
            0,
            "Supports presentations.",
        ),
        (
            "SOCIAL_RESEARCH",
            3,
            3,
            0,
            "Helps understand audiences.",
        ),
    ),
    "SOCIAL_WORKER": (
        (
            "ACTIVE_LISTENING",
            5,
            4,
            1,
            "Supports understanding client needs.",
        ),
        (
            "CASE_MANAGEMENT",
            5,
            4,
            1,
            "Coordinates services and follow-up.",
        ),
        (
            "COMMUNITY_OUTREACH",
            4,
            3,
            0,
            "Connects people with resources.",
        ),
        (
            "CONFLICT_RESOLUTION",
            3,
            3,
            0,
            "Supports respectful problem solving.",
        ),
    ),
}


RESOURCE_ROWS: tuple[dict[str, Any], ...] = (
    {
        "title": "JSU Career Services",
        "resource_type": "career_services",
        "description": (
            "Career advising, career events, employer connections, and "
            "student career support for JSU students."
        ),
        "provider_name": "Jackson State University Career Services",
        "delivery_method": "hybrid",
        "audience_type": "all_students",
        "eligibility_notes": (
            "Available to currently enrolled JSU students."
        ),
    },
    {
        "title": "Resume and Cover Letter Support",
        "resource_type": "resume_support",
        "description": (
            "Guidance for creating resumes and cover letters that reflect "
            "a student's major, skills, and career direction."
        ),
        "provider_name": "Jackson State University Career Services",
        "delivery_method": "hybrid",
        "audience_type": "all_students",
        "eligibility_notes": (
            "Students should bring a current draft for feedback."
        ),
    },
    {
        "title": "Interview Preparation",
        "resource_type": "interview_practice",
        "description": (
            "Practice resources for behavioral, technical, and "
            "field-specific interviews."
        ),
        "provider_name": "Jackson State University Career Services",
        "delivery_method": "hybrid",
        "audience_type": "all_students",
        "eligibility_notes": (
            "Appointment availability may vary."
        ),
    },
    {
        "title": "Internship and Experiential Learning Resources",
        "resource_type": "experiential_learning",
        "description": (
            "Resources for internships, projects, service learning, and "
            "other professional experiences."
        ),
        "provider_name": "Jackson State University",
        "delivery_method": "online",
        "audience_type": "all_students",
        "eligibility_notes": (
            "Students should confirm program eligibility."
        ),
    },
    {
        "title": "Graduate and Professional School Resources",
        "resource_type": "graduate_school",
        "description": (
            "Planning resources for graduate programs, applications, "
            "professional programs, and funding."
        ),
        "provider_name": "Jackson State University",
        "delivery_method": "online",
        "audience_type": "all_students",
        "eligibility_notes": (
            "Requirements vary by program and institution."
        ),
    },
)


def verify_seed_environment() -> None:
    """Prevent development seed data from running in production."""

    if settings.ENVIRONMENT.strip().lower() in {"production", "prod"}:
        raise RuntimeError(
            "The development seed script cannot run in production."
        )


def _get_or_create(
    session: Session,
    model: Any,
    lookup: dict[str, Any],
    values: dict[str, Any] | None = None,
) -> tuple[Any, bool]:
    """
    Find a row using its natural key or create it if it is missing.

    Returns:
        A tuple containing the database object and whether it was created.
    """

    existing = session.execute(
        select(model).filter_by(**lookup)
    ).scalars().first()

    if existing is not None:
        return existing, False

    payload = dict(lookup)

    if values:
        payload.update(values)

    created = model(**payload)
    session.add(created)
    session.flush()

    return created, True


def seed_roles(session: Session) -> int:
    """Insert approved roles that are missing."""

    added = 0

    for row in ROLE_ROWS:
        _, created = _get_or_create(
            session=session,
            model=Role,
            lookup={"name": row["name"]},
            values={"description": row["description"]},
        )
        added += int(created)

    return added


def seed_industries(session: Session) -> int:
    """Insert broad industries used by TigerPad career paths."""

    added = 0

    for row in INDUSTRY_ROWS:
        _, created = _get_or_create(
            session=session,
            model=Industry,
            lookup={"industry_code": row["industry_code"]},
            values={
                "name": row["name"],
                "description": row["description"],
            },
        )
        added += int(created)

    return added


def seed_career_paths(session: Session) -> int:
    """Insert generalized career paths linked to industries."""

    industries = {
        industry.industry_code: industry
        for industry in session.execute(
            select(Industry)
        ).scalars()
    }

    added = 0

    for row in CAREER_PATH_ROWS:
        industry = industries.get(row["industry_code"])

        if industry is None:
            raise RuntimeError(
                f"Missing industry: {row['industry_code']}"
            )

        _, created = _get_or_create(
            session=session,
            model=CareerPath,
            lookup={
                "career_path_code": row["career_path_code"],
            },
            values={
                "industry_id": industry.industry_id,
                "name": row["name"],
                "description": row["description"],
                "typical_education_level": (
                    row["typical_education_level"]
                ),
            },
        )
        added += int(created)

    return added


def seed_skills(session: Session) -> int:
    """Insert diverse academic and professional skills."""

    added = 0

    for row in SKILL_ROWS:
        _, created = _get_or_create(
            session=session,
            model=Skill,
            lookup={"skill_code": row["skill_code"]},
            values={
                "name": row["name"],
                "category": row["category"],
                "description": row["description"],
            },
        )
        added += int(created)

    return added


def seed_career_path_skills(session: Session) -> int:
    """Connect selected career paths to their target skills."""

    career_paths = {
        path.career_path_code: path
        for path in session.execute(
            select(CareerPath)
        ).scalars()
    }

    skills = {
        skill.skill_code: skill
        for skill in session.execute(
            select(Skill)
        ).scalars()
    }

    added = 0

    for career_path_code, skill_rows in (
        CAREER_PATH_SKILL_ROWS.items()
    ):
        career_path = career_paths.get(career_path_code)

        if career_path is None:
            raise RuntimeError(
                f"Missing career path: {career_path_code}"
            )

        for (
            skill_code,
            importance,
            target,
            required,
            notes,
        ) in skill_rows:
            skill = skills.get(skill_code)

            if skill is None:
                raise RuntimeError(
                    f"Missing skill: {skill_code}"
                )

            _, created = _get_or_create(
                session=session,
                model=CareerPathSkill,
                lookup={
                    "career_path_id": career_path.career_path_id,
                    "skill_id": skill.skill_id,
                },
                values={
                    "importance_level": importance,
                    "target_proficiency_level": target,
                    "is_required": required,
                    "notes": notes,
                },
            )
            added += int(created)

    return added


def seed_career_resources(session: Session) -> int:
    """
    Insert JSU career resources without duplicate titles.

    Official URLs are intentionally not inserted until Jay approves them.
    """

    added = 0

    for row in RESOURCE_ROWS:
        values = {
            key: value
            for key, value in row.items()
            if key != "title"
        }

        _, created = _get_or_create(
            session=session,
            model=Resource,
            lookup={"title": row["title"]},
            values=values,
        )
        added += int(created)

    return added


def seed_development_accounts(session: Session) -> int:
    """
    Keep development-account creation disabled until authentication is ready.
    """

    _ = session
    return 0


def seed_database() -> dict[str, Any]:
    """
    Run the complete idempotent TigerPad seed process.

    The database tables are already managed through MySQL Workbench, so this
    function does not call create_all_tables().
    """

    verify_seed_environment()

    if not check_database_connection():
        raise ConnectionError(
            "TigerPad could not connect to the configured database."
        )

    session = SessionLocal()

    try:
        seed_results = {
            "roles_added": seed_roles(session),
            "industries_added": seed_industries(session),
            "skills_added": seed_skills(session),
            "career_paths_added": seed_career_paths(session),
            "career_path_skills_added": (
                seed_career_path_skills(session)
            ),
            "career_resources_added": (
                seed_career_resources(session)
            ),
            "development_accounts_added": (
                seed_development_accounts(session)
            ),
        }

        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()

    return {
        "success": True,
        "environment": settings.ENVIRONMENT,
        "database": settings.DATABASE_NAME,
        "registered_tables": sorted(
            Base.metadata.tables.keys()
        ),
        "seed_results": seed_results,
        "message": (
            "TigerPad seed process completed without duplicate inserts."
        ),
    }


def main() -> None:
    """Run the TigerPad seed process from the command line."""

    try:
        result = seed_database()

        print(result["message"])
        print(f"Environment: {result['environment']}")
        print(f"Database: {result['database']}")
        print(
            "Registered tables: "
            f"{len(result['registered_tables'])}"
        )
        print(f"Seed results: {result['seed_results']}")

    except Exception:
        print(
            "The seed process failed; all changes were rolled back."
        )
        raise


if __name__ == "__main__":
    main()