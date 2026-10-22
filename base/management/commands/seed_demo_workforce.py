"""
Fill the live database with realistic employees, recruitments, and onboarding.

Idempotent. Tagged with email domain ``@demo.dsghrms.local`` and recruitment
titles starting with ``Demo:`` so ``--clear`` can remove only this data.

Usage:
    python manage.py seed_demo_workforce
    python manage.py seed_demo_workforce --clear
"""

from __future__ import annotations

import os
from datetime import date, time, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

EMAIL_DOMAIN = "demo.dsghrms.local"
TITLE_PREFIX = "Demo:"
DEFAULT_PASSWORD = os.environ.get("DEMO_WORKFORCE_PASSWORD", "DemoHRMS123!")
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"

DEPARTMENTS = (
    "Administration",
    "Human Resources",
    "Engineering",
    "Sales",
    "Finance",
    "Information Technology",
    "Operations",
)

JOB_SETUP = (
    ("Administration", "Chief Executive Officer", ("Chief Executive",)),
    ("Human Resources", "HR Manager", ("People Operations",)),
    ("Human Resources", "Talent Acquisition Specialist", ("Recruiter",)),
    ("Human Resources", "HR Generalist", ("HR Operations",)),
    ("Engineering", "Engineering Manager", ("Engineering Lead",)),
    ("Engineering", "Senior Software Engineer", ("Backend Engineer",)),
    ("Engineering", "Software Engineer", ("Full Stack Engineer",)),
    ("Engineering", "Frontend Engineer", ("UI Engineer",)),
    ("Engineering", "DevOps Engineer", ("Site Reliability",)),
    ("Engineering", "QA Engineer", ("Quality Analyst",)),
    ("Sales", "Sales Manager", ("Sales Lead",)),
    ("Sales", "Account Executive", ("Enterprise Sales",)),
    ("Sales", "Sales Development Representative", ("Outbound Sales",)),
    ("Finance", "Finance Manager", ("Financial Controller",)),
    ("Finance", "Accountant", ("Accounts Payable",)),
    ("Information Technology", "IT Manager", ("IT Operations",)),
    ("Information Technology", "IT Support Specialist", ("Desktop Support",)),
    ("Operations", "Operations Manager", ("Office Operations",)),
    ("Operations", "Office Coordinator", ("Administration",)),
)

CEO_EMAIL = f"kamran.shah@{EMAIL_DOMAIN}"

PEOPLE = (
    {
        "first_name": "Kamran",
        "last_name": "Shah",
        "email": CEO_EMAIL,
        "phone": "+923001110100",
        "badge_id": "DSG-100",
        "gender": "male",
        "dob": date(1979, 5, 11),
        "city": "Karachi",
        "department": "Administration",
        "job_position": "Chief Executive Officer",
        "job_role": "Chief Executive",
        "manager_email": None,
        "salary": 650000,
        "experience": 22,
        "qualification": "MBA Strategy",
        "marital_status": "married",
        "joining": date(2016, 1, 4),
        "create_user": True,
    },
    {
        "first_name": "Nadia",
        "last_name": "Rahman",
        "email": f"nadia.rahman@{EMAIL_DOMAIN}",
        "phone": "+923001110101",
        "badge_id": "DSG-101",
        "gender": "female",
        "dob": date(1988, 3, 14),
        "city": "Karachi",
        "department": "Human Resources",
        "job_position": "HR Manager",
        "job_role": "People Operations",
        "manager_email": CEO_EMAIL,
        "salary": 280000,
        "experience": 12,
        "qualification": "MBA Human Resources",
        "marital_status": "married",
        "joining": date(2019, 4, 1),
        "create_user": True,
    },
    {
        "first_name": "Omar",
        "last_name": "Siddiqui",
        "email": f"omar.siddiqui@{EMAIL_DOMAIN}",
        "phone": "+923001110102",
        "badge_id": "DSG-102",
        "gender": "male",
        "dob": date(1992, 7, 22),
        "city": "Karachi",
        "department": "Human Resources",
        "job_position": "Talent Acquisition Specialist",
        "job_role": "Recruiter",
        "manager_email": f"nadia.rahman@{EMAIL_DOMAIN}",
        "salary": 165000,
        "experience": 7,
        "qualification": "BS Psychology",
        "marital_status": "single",
        "joining": date(2021, 6, 15),
        "create_user": True,
    },
    {
        "first_name": "Hira",
        "last_name": "Malik",
        "email": f"hira.malik@{EMAIL_DOMAIN}",
        "phone": "+923001110103",
        "badge_id": "DSG-103",
        "gender": "female",
        "dob": date(1995, 11, 2),
        "city": "Lahore",
        "department": "Human Resources",
        "job_position": "HR Generalist",
        "job_role": "HR Operations",
        "manager_email": f"nadia.rahman@{EMAIL_DOMAIN}",
        "salary": 140000,
        "experience": 5,
        "qualification": "BBA",
        "marital_status": "married",
        "joining": date(2022, 1, 10),
        "create_user": True,
    },
    {
        "first_name": "Zain",
        "last_name": "Abbas",
        "email": f"zain.abbas@{EMAIL_DOMAIN}",
        "phone": "+923001110104",
        "badge_id": "DSG-104",
        "gender": "male",
        "dob": date(1986, 1, 19),
        "city": "Karachi",
        "department": "Engineering",
        "job_position": "Engineering Manager",
        "job_role": "Engineering Lead",
        "manager_email": CEO_EMAIL,
        "salary": 420000,
        "experience": 14,
        "qualification": "MS Computer Science",
        "marital_status": "married",
        "joining": date(2018, 9, 3),
        "create_user": True,
    },
    {
        "first_name": "Fatima",
        "last_name": "Noor",
        "email": f"fatima.noor@{EMAIL_DOMAIN}",
        "phone": "+923001110105",
        "badge_id": "DSG-105",
        "gender": "female",
        "dob": date(1993, 5, 8),
        "city": "Karachi",
        "department": "Engineering",
        "job_position": "Senior Software Engineer",
        "job_role": "Backend Engineer",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 310000,
        "experience": 9,
        "qualification": "BS Software Engineering",
        "marital_status": "single",
        "joining": date(2020, 2, 17),
        "create_user": True,
    },
    {
        "first_name": "Ali",
        "last_name": "Raza",
        "email": f"ali.raza@{EMAIL_DOMAIN}",
        "phone": "+923001110106",
        "badge_id": "DSG-106",
        "gender": "male",
        "dob": date(1996, 8, 30),
        "city": "Islamabad",
        "department": "Engineering",
        "job_position": "Software Engineer",
        "job_role": "Full Stack Engineer",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 210000,
        "experience": 4,
        "qualification": "BS Computer Science",
        "marital_status": "single",
        "joining": date(2023, 3, 6),
        "create_user": True,
    },
    {
        "first_name": "Sana",
        "last_name": "Iqbal",
        "email": f"sana.iqbal@{EMAIL_DOMAIN}",
        "phone": "+923001110107",
        "badge_id": "DSG-107",
        "gender": "female",
        "dob": date(1994, 12, 12),
        "city": "Lahore",
        "department": "Engineering",
        "job_position": "QA Engineer",
        "job_role": "Quality Analyst",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 175000,
        "experience": 6,
        "qualification": "BS Information Technology",
        "marital_status": "married",
        "joining": date(2021, 11, 1),
        "create_user": True,
    },
    {
        "first_name": "Bilal",
        "last_name": "Hassan",
        "email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "phone": "+923001110108",
        "badge_id": "DSG-108",
        "gender": "male",
        "dob": date(1989, 4, 4),
        "city": "Karachi",
        "department": "Sales",
        "job_position": "Sales Manager",
        "job_role": "Sales Lead",
        "manager_email": CEO_EMAIL,
        "salary": 300000,
        "experience": 11,
        "qualification": "MBA Marketing",
        "marital_status": "married",
        "joining": date(2019, 8, 12),
        "create_user": True,
    },
    {
        "first_name": "Ayesha",
        "last_name": "Kamal",
        "email": f"ayesha.kamal@{EMAIL_DOMAIN}",
        "phone": "+923001110109",
        "badge_id": "DSG-109",
        "gender": "female",
        "dob": date(1997, 2, 27),
        "city": "Karachi",
        "department": "Sales",
        "job_position": "Account Executive",
        "job_role": "Enterprise Sales",
        "manager_email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "salary": 155000,
        "experience": 3,
        "qualification": "BBA Marketing",
        "marital_status": "single",
        "joining": date(2024, 1, 8),
        "create_user": True,
    },
    {
        "first_name": "Imran",
        "last_name": "Qureshi",
        "email": f"imran.qureshi@{EMAIL_DOMAIN}",
        "phone": "+923001110110",
        "badge_id": "DSG-110",
        "gender": "male",
        "dob": date(1987, 9, 16),
        "city": "Karachi",
        "department": "Finance",
        "job_position": "Finance Manager",
        "job_role": "Financial Controller",
        "manager_email": CEO_EMAIL,
        "salary": 340000,
        "experience": 13,
        "qualification": "ACCA",
        "marital_status": "married",
        "joining": date(2017, 5, 22),
        "create_user": True,
    },
    {
        "first_name": "Mehwish",
        "last_name": "Tariq",
        "email": f"mehwish.tariq@{EMAIL_DOMAIN}",
        "phone": "+923001110111",
        "badge_id": "DSG-111",
        "gender": "female",
        "dob": date(1998, 6, 5),
        "city": "Lahore",
        "department": "Finance",
        "job_position": "Accountant",
        "job_role": "Accounts Payable",
        "manager_email": f"imran.qureshi@{EMAIL_DOMAIN}",
        "salary": 125000,
        "experience": 3,
        "qualification": "B.Com",
        "marital_status": "single",
        "joining": date(2024, 4, 1),
        "create_user": True,
    },
    {
        "first_name": "Hamza",
        "last_name": "Sheikh",
        "email": f"hamza.sheikh@{EMAIL_DOMAIN}",
        "phone": "+923001110112",
        "badge_id": "DSG-112",
        "gender": "male",
        "dob": date(1991, 10, 21),
        "city": "Karachi",
        "department": "Information Technology",
        "job_position": "IT Manager",
        "job_role": "IT Operations",
        "manager_email": CEO_EMAIL,
        "salary": 260000,
        "experience": 10,
        "qualification": "BS Computer Networks",
        "marital_status": "married",
        "joining": date(2020, 7, 13),
        "create_user": True,
    },
    {
        "first_name": "Rabia",
        "last_name": "Yousaf",
        "email": f"rabia.yousaf@{EMAIL_DOMAIN}",
        "phone": "+923001110113",
        "badge_id": "DSG-113",
        "gender": "female",
        "dob": date(1999, 1, 9),
        "city": "Karachi",
        "department": "Information Technology",
        "job_position": "IT Support Specialist",
        "job_role": "Desktop Support",
        "manager_email": f"hamza.sheikh@{EMAIL_DOMAIN}",
        "salary": 110000,
        "experience": 2,
        "qualification": "Diploma in IT",
        "marital_status": "single",
        "joining": date(2024, 9, 2),
        "create_user": True,
    },
    {
        "first_name": "Saad",
        "last_name": "Farooq",
        "email": f"saad.farooq@{EMAIL_DOMAIN}",
        "phone": "+923001110114",
        "badge_id": "DSG-114",
        "gender": "male",
        "dob": date(1990, 3, 3),
        "city": "Karachi",
        "department": "Operations",
        "job_position": "Operations Manager",
        "job_role": "Office Operations",
        "manager_email": CEO_EMAIL,
        "salary": 230000,
        "experience": 9,
        "qualification": "MBA Operations",
        "marital_status": "married",
        "joining": date(2021, 2, 1),
        "create_user": True,
    },
    {
        "first_name": "Zara",
        "last_name": "Ahmed",
        "email": f"zara.ahmed@{EMAIL_DOMAIN}",
        "phone": "+923001110115",
        "badge_id": "DSG-115",
        "gender": "female",
        "dob": date(2000, 8, 18),
        "city": "Karachi",
        "department": "Operations",
        "job_position": "Office Coordinator",
        "job_role": "Administration",
        "manager_email": f"saad.farooq@{EMAIL_DOMAIN}",
        "salary": 95000,
        "experience": 2,
        "qualification": "BA English",
        "marital_status": "single",
        "joining": date(2025, 1, 6),
        "create_user": True,
    },
    {
        "first_name": "Tariq",
        "last_name": "Mehmood",
        "email": f"tariq.mehmood@{EMAIL_DOMAIN}",
        "phone": "+923001110116",
        "badge_id": "DSG-116",
        "gender": "male",
        "dob": date(1994, 7, 11),
        "city": "Islamabad",
        "department": "Engineering",
        "job_position": "Software Engineer",
        "job_role": "Full Stack Engineer",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 195000,
        "experience": 5,
        "qualification": "BS Software Engineering",
        "marital_status": "married",
        "joining": date(2022, 8, 15),
        "create_user": True,
    },
    {
        "first_name": "Maham",
        "last_name": "Javed",
        "email": f"maham.javed@{EMAIL_DOMAIN}",
        "phone": "+923001110117",
        "badge_id": "DSG-117",
        "gender": "female",
        "dob": date(1996, 4, 25),
        "city": "Lahore",
        "department": "Sales",
        "job_position": "Account Executive",
        "job_role": "Enterprise Sales",
        "manager_email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "salary": 148000,
        "experience": 4,
        "qualification": "BS Business Administration",
        "marital_status": "single",
        "joining": date(2023, 10, 9),
        "create_user": True,
    },
    {
        "first_name": "Usman",
        "last_name": "Ali",
        "email": f"usman.ali@{EMAIL_DOMAIN}",
        "phone": "+923001110118",
        "badge_id": "DSG-118",
        "gender": "male",
        "dob": date(1992, 12, 1),
        "city": "Karachi",
        "department": "Human Resources",
        "job_position": "HR Generalist",
        "job_role": "HR Operations",
        "manager_email": f"nadia.rahman@{EMAIL_DOMAIN}",
        "salary": 132000,
        "experience": 6,
        "qualification": "MA Human Resource Management",
        "marital_status": "married",
        "joining": date(2022, 5, 16),
        "create_user": True,
    },
    {
        "first_name": "Farah",
        "last_name": "Aziz",
        "email": f"farah.aziz@{EMAIL_DOMAIN}",
        "phone": "+923001110119",
        "badge_id": "DSG-119",
        "gender": "female",
        "dob": date(1995, 9, 14),
        "city": "Karachi",
        "department": "Engineering",
        "job_position": "Frontend Engineer",
        "job_role": "UI Engineer",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 205000,
        "experience": 5,
        "qualification": "BS Computer Science",
        "marital_status": "single",
        "joining": date(2023, 6, 12),
        "create_user": True,
    },
    {
        "first_name": "Rehan",
        "last_name": "Malik",
        "email": f"rehan.malik@{EMAIL_DOMAIN}",
        "phone": "+923001110120",
        "badge_id": "DSG-120",
        "gender": "male",
        "dob": date(1991, 2, 8),
        "city": "Islamabad",
        "department": "Engineering",
        "job_position": "DevOps Engineer",
        "job_role": "Site Reliability",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 240000,
        "experience": 8,
        "qualification": "BS Information Systems",
        "marital_status": "married",
        "joining": date(2022, 3, 21),
        "create_user": True,
    },
    {
        "first_name": "Lubna",
        "last_name": "Sheikh",
        "email": f"lubna.sheikh@{EMAIL_DOMAIN}",
        "phone": "+923001110121",
        "badge_id": "DSG-121",
        "gender": "female",
        "dob": date(1993, 11, 29),
        "city": "Lahore",
        "department": "Engineering",
        "job_position": "Senior Software Engineer",
        "job_role": "Backend Engineer",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 295000,
        "experience": 8,
        "qualification": "MS Software Engineering",
        "marital_status": "married",
        "joining": date(2021, 4, 5),
        "create_user": True,
    },
    {
        "first_name": "Maryam",
        "last_name": "Gul",
        "email": f"maryam.gul@{EMAIL_DOMAIN}",
        "phone": "+923001110122",
        "badge_id": "DSG-122",
        "gender": "female",
        "dob": date(1998, 7, 19),
        "city": "Karachi",
        "department": "Engineering",
        "job_position": "QA Engineer",
        "job_role": "Quality Analyst",
        "manager_email": f"zain.abbas@{EMAIL_DOMAIN}",
        "salary": 155000,
        "experience": 3,
        "qualification": "BS Software Engineering",
        "marital_status": "single",
        "joining": date(2024, 2, 12),
        "create_user": True,
    },
    {
        "first_name": "Kashif",
        "last_name": "Anwar",
        "email": f"kashif.anwar@{EMAIL_DOMAIN}",
        "phone": "+923001110123",
        "badge_id": "DSG-123",
        "gender": "male",
        "dob": date(1997, 1, 23),
        "city": "Karachi",
        "department": "Sales",
        "job_position": "Sales Development Representative",
        "job_role": "Outbound Sales",
        "manager_email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "salary": 120000,
        "experience": 2,
        "qualification": "BBA",
        "marital_status": "single",
        "joining": date(2024, 7, 1),
        "create_user": True,
    },
    {
        "first_name": "Haroon",
        "last_name": "Saeed",
        "email": f"haroon.saeed@{EMAIL_DOMAIN}",
        "phone": "+923001110124",
        "badge_id": "DSG-124",
        "gender": "male",
        "dob": date(1994, 6, 16),
        "city": "Lahore",
        "department": "Sales",
        "job_position": "Account Executive",
        "job_role": "Enterprise Sales",
        "manager_email": f"bilal.hassan@{EMAIL_DOMAIN}",
        "salary": 170000,
        "experience": 5,
        "qualification": "MBA Marketing",
        "marital_status": "married",
        "joining": date(2023, 1, 16),
        "create_user": True,
    },
    {
        "first_name": "Nida",
        "last_name": "Parveen",
        "email": f"nida.parveen@{EMAIL_DOMAIN}",
        "phone": "+923001110125",
        "badge_id": "DSG-125",
        "gender": "female",
        "dob": date(1996, 10, 3),
        "city": "Karachi",
        "department": "Finance",
        "job_position": "Accountant",
        "job_role": "Accounts Payable",
        "manager_email": f"imran.qureshi@{EMAIL_DOMAIN}",
        "salary": 118000,
        "experience": 4,
        "qualification": "ACCA Affiliate",
        "marital_status": "single",
        "joining": date(2023, 9, 4),
        "create_user": True,
    },
    {
        "first_name": "Asad",
        "last_name": "Butt",
        "email": f"asad.butt@{EMAIL_DOMAIN}",
        "phone": "+923001110126",
        "badge_id": "DSG-126",
        "gender": "male",
        "dob": date(1999, 3, 27),
        "city": "Karachi",
        "department": "Information Technology",
        "job_position": "IT Support Specialist",
        "job_role": "Desktop Support",
        "manager_email": f"hamza.sheikh@{EMAIL_DOMAIN}",
        "salary": 105000,
        "experience": 2,
        "qualification": "BS Computer Science",
        "marital_status": "single",
        "joining": date(2025, 3, 3),
        "create_user": True,
    },
    {
        "first_name": "Ehsan",
        "last_name": "Ali",
        "email": f"ehsan.ali@{EMAIL_DOMAIN}",
        "phone": "+923001110127",
        "badge_id": "DSG-127",
        "gender": "male",
        "dob": date(1992, 8, 9),
        "city": "Karachi",
        "department": "Operations",
        "job_position": "Office Coordinator",
        "job_role": "Administration",
        "manager_email": f"saad.farooq@{EMAIL_DOMAIN}",
        "salary": 98000,
        "experience": 4,
        "qualification": "BA Public Administration",
        "marital_status": "married",
        "joining": date(2023, 5, 22),
        "create_user": True,
    },
    {
        "first_name": "Saima",
        "last_name": "Riaz",
        "email": f"saima.riaz@{EMAIL_DOMAIN}",
        "phone": "+923001110128",
        "badge_id": "DSG-128",
        "gender": "female",
        "dob": date(1994, 12, 21),
        "city": "Lahore",
        "department": "Human Resources",
        "job_position": "Talent Acquisition Specialist",
        "job_role": "Recruiter",
        "manager_email": f"nadia.rahman@{EMAIL_DOMAIN}",
        "salary": 150000,
        "experience": 6,
        "qualification": "MS HRM",
        "marital_status": "married",
        "joining": date(2022, 11, 7),
        "create_user": True,
    },
)

RECRUIT_STAGES = (
    ("Applied", "applied", 0),
    ("Screening", "initial", 1),
    ("Skills Assessment", "test", 2),
    ("Interview", "interview", 3),
    ("Offer / Hired", "hired", 4),
    ("Not Selected", "cancelled", 5),
)

ONBOARD_STAGES = (
    ("Welcome / Initial", 0, False),
    ("Documentation", 1, False),
    ("IT Setup", 2, False),
    ("Orientation", 3, False),
    ("First Week Complete", 4, True),
)

ONBOARD_TASKS = {
    "Welcome / Initial": (
        ("Send welcome email", True),
        ("Assign onboarding buddy", True),
        ("Share company handbook", True),
        ("Add to Slack / Teams and email groups", False),
    ),
    "Documentation": (
        ("Collect CNIC and bank details", True),
        ("Sign employment contract", True),
        ("Complete tax declaration", True),
        ("Submit emergency contact form", False),
    ),
    "IT Setup": (
        ("Provision laptop and accounts", True),
        ("Grant system access", True),
        ("Complete security training", True),
        ("Issue access card and headset", False),
    ),
    "Orientation": (
        ("Attend HR orientation", True),
        ("Meet reporting manager", True),
        ("Tour office / tools walkthrough", True),
        ("Shadow a teammate for half a day", False),
    ),
    "First Week Complete": (
        ("30-day goals agreed", True),
        ("First-week feedback collected", True),
        ("Confirm payroll details with Finance", False),
    ),
}

RECRUITMENTS = (
    {
        "title": f"{TITLE_PREFIX} Backend Engineer 2026",
        "job_position": "Software Engineer",
        "vacancy": 3,
        "start_offset": 21,
        "end_offset": 45,
        "skills": ("Python", "Django", "Postgresql", "Rest apis"),
        "managers": (
            f"zain.abbas@{EMAIL_DOMAIN}",
            f"omar.siddiqui@{EMAIL_DOMAIN}",
        ),
        "description": (
            "<p>We are hiring a Backend Engineer to build and maintain DSG HR "
            "platform services. Strong Python and Django experience required.</p>"
        ),
        "candidates": (
            ("Amina Shah", "applied", "application", "company_career_site", "female", None, False),
            ("Hassan Jamil", "applied", "application", "job_board", "male", None, False),
            ("Noor Fatima", "initial", "application", "employee_referral", "female", 3.5, False),
            ("Danish Rauf", "test", "software", None, "male", 4.0, False),
            ("Leila Rahman", "interview", "application", "linkedin", "female", 4.5, False),
            ("Adeel Khan", "hired", "application", "company_career_site", "male", 5.0, True),
            ("Saba Nadeem", "hired", "software", "employee_referral", "female", 4.5, True),
            ("Farhan Mir", "cancelled", "application", "job_board", "male", 2.0, False),
        ),
    },
    {
        "title": f"{TITLE_PREFIX} HR Business Partner",
        "job_position": "HR Generalist",
        "vacancy": 2,
        "start_offset": 18,
        "end_offset": 50,
        "skills": ("Employee relations", "Hr analytics", "Communication"),
        "managers": (
            f"nadia.rahman@{EMAIL_DOMAIN}",
            f"omar.siddiqui@{EMAIL_DOMAIN}",
        ),
        "description": (
            "<p>HR Business Partner to support Engineering and Sales. "
            "Experience with performance, onboarding, and employee relations.</p>"
        ),
        "candidates": (
            ("Komal Saeed", "applied", "application", "social_media", "female", None, False),
            ("Yasir Mehmood", "initial", "application", "job_board", "male", 3.0, False),
            ("Anam Bukhari", "interview", "application", "employee_referral", "female", 4.5, False),
            ("Sarah Hussain", "hired", "application", "company_career_site", "female", 5.0, True),
            ("Noman Iftikhar", "cancelled", "software", None, "male", None, False),
        ),
    },
    {
        "title": f"{TITLE_PREFIX} Account Executive",
        "job_position": "Account Executive",
        "vacancy": 2,
        "start_offset": 12,
        "end_offset": 40,
        "skills": ("Negotiation", "Crm", "B2b sales"),
        "managers": (
            f"bilal.hassan@{EMAIL_DOMAIN}",
            f"omar.siddiqui@{EMAIL_DOMAIN}",
        ),
        "description": (
            "<p>Enterprise Account Executive for the Pakistan market. "
            "Quota-carrying role with existing pipeline support.</p>"
        ),
        "candidates": (
            ("Rida Anwar", "applied", "application", "social_media", "female", None, False),
            ("Shahzaib Ali", "test", "application", "job_board", "male", 3.5, False),
            ("Hina Qazi", "interview", "software", "recruiter_headhunter", "female", 4.0, False),
            ("Waleed Asif", "hired", "application", "employee_referral", "male", 4.5, True),
            ("Iqra Naseer", "cancelled", "application", "company_career_site", "female", 2.5, False),
        ),
    },
    {
        "title": f"{TITLE_PREFIX} IT Support Specialist",
        "job_position": "IT Support Specialist",
        "vacancy": 1,
        "start_offset": 9,
        "end_offset": 30,
        "skills": ("Windows", "Helpdesk", "Active directory"),
        "managers": (
            f"hamza.sheikh@{EMAIL_DOMAIN}",
            f"omar.siddiqui@{EMAIL_DOMAIN}",
        ),
        "description": (
            "<p>On-site IT Support Specialist for Karachi HQ. Hardware, "
            "accounts, and first-line application support.</p>"
        ),
        "candidates": (
            ("Arsalan Haider", "applied", "application", "job_board", "male", None, False),
            ("Nimra Aziz", "initial", "application", "company_career_site", "female", 3.5, False),
            ("Junaid Akram", "hired", "software", "employee_referral", "male", 4.5, True),
            ("Maria Khan", "cancelled", "application", "social_media", "female", None, False),
        ),
    },
    {
        "title": f"{TITLE_PREFIX} Frontend Engineer",
        "job_position": "Frontend Engineer",
        "vacancy": 2,
        "start_offset": 16,
        "end_offset": 42,
        "skills": ("Javascript", "React", "Css", "Accessibility"),
        "managers": (
            f"zain.abbas@{EMAIL_DOMAIN}",
            f"omar.siddiqui@{EMAIL_DOMAIN}",
        ),
        "description": (
            "<p>Frontend Engineer to own DSG product UI. React, design-system "
            "thinking, and accessibility experience required.</p>"
        ),
        "candidates": (
            ("Zainab Iftikhar", "applied", "application", "company_career_site", "female", None, False),
            ("Taha Rizvi", "applied", "application", "job_board", "male", None, False),
            ("Hira Nasir", "initial", "application", "social_media", "female", 3.5, False),
            ("Owais Jafri", "test", "software", None, "male", 4.0, False),
            ("Sundus Bari", "interview", "application", "employee_referral", "female", 4.5, False),
            ("Muneeb Aslam", "hired", "application", "company_career_site", "male", 5.0, True),
            ("Areeba Zahid", "hired", "software", "job_board", "female", 4.5, True),
            ("Faisal Qadir", "cancelled", "application", "social_media", "male", 2.0, False),
        ),
    },
    {
        "title": f"{TITLE_PREFIX} DevOps Engineer",
        "job_position": "DevOps Engineer",
        "vacancy": 1,
        "start_offset": 11,
        "end_offset": 35,
        "skills": ("Aws", "Docker", "Kubernetes", "Ci/cd"),
        "managers": (
            f"zain.abbas@{EMAIL_DOMAIN}",
            f"hamza.sheikh@{EMAIL_DOMAIN}",
        ),
        "description": (
            "<p>DevOps Engineer for production reliability, CI/CD, and cloud "
            "cost control across DSG environments.</p>"
        ),
        "candidates": (
            ("Saifullah Khan", "applied", "application", "job_board", "male", None, False),
            ("Mahira Sohail", "initial", "application", "company_career_site", "female", 3.5, False),
            ("Umer Durrani", "interview", "software", "recruiter_headhunter", "male", 4.5, False),
            ("Hammad Iqbal", "hired", "application", "employee_referral", "male", 5.0, True),
            ("Kiran Batool", "cancelled", "application", "social_media", "female", None, False),
        ),
    },
    {
        "title": f"{TITLE_PREFIX} Sales Development Representative",
        "job_position": "Sales Development Representative",
        "vacancy": 2,
        "start_offset": 8,
        "end_offset": 28,
        "skills": ("Prospecting", "Cold calling", "Crm"),
        "managers": (
            f"bilal.hassan@{EMAIL_DOMAIN}",
            f"saima.riaz@{EMAIL_DOMAIN}",
        ),
        "description": (
            "<p>SDR to book qualified meetings for Account Executives in "
            "Karachi and Lahore.</p>"
        ),
        "candidates": (
            ("Laiba Shah", "applied", "application", "social_media", "female", None, False),
            ("Rohail Naeem", "test", "application", "job_board", "male", 3.0, False),
            ("Anum Fawad", "interview", "application", "employee_referral", "female", 4.0, False),
            ("Shayan Raza", "hired", "application", "company_career_site", "male", 4.5, True),
            ("Bushra Ali", "cancelled", "software", None, "female", 2.0, False),
        ),
    },
)

ASSET_CATEGORIES = (
    ("Laptop", "Company laptops assigned to employees."),
    ("Monitor", "External displays for workstations."),
    ("Mobile Phone", "Corporate mobile phones."),
    ("Headset", "Headsets for calls and meetings."),
    ("Access Card", "Building and office access cards."),
)

# serial, name, category, cost, assignee email, returned?
ASSET_RECORDS = (
    ("DSG-AST-001", "MacBook Pro 14", "Laptop", 420000, f"zain.abbas@{EMAIL_DOMAIN}", False),
    ("DSG-AST-002", "MacBook Pro 14", "Laptop", 420000, f"fatima.noor@{EMAIL_DOMAIN}", False),
    ("DSG-AST-003", "Dell XPS 15", "Laptop", 310000, f"ali.raza@{EMAIL_DOMAIN}", False),
    ("DSG-AST-004", "Dell XPS 15", "Laptop", 310000, f"sana.iqbal@{EMAIL_DOMAIN}", True),
    ("DSG-AST-005", "Lenovo ThinkPad T14", "Laptop", 245000, f"nadia.rahman@{EMAIL_DOMAIN}", False),
    ("DSG-AST-006", "Lenovo ThinkPad T14", "Laptop", 245000, f"omar.siddiqui@{EMAIL_DOMAIN}", False),
    ("DSG-AST-007", "Dell 27 Monitor", "Monitor", 65000, f"zain.abbas@{EMAIL_DOMAIN}", False),
    ("DSG-AST-008", "Dell 27 Monitor", "Monitor", 65000, f"imran.qureshi@{EMAIL_DOMAIN}", True),
    ("DSG-AST-009", "Samsung A55", "Mobile Phone", 98000, f"bilal.hassan@{EMAIL_DOMAIN}", False),
    ("DSG-AST-010", "Samsung A55", "Mobile Phone", 98000, f"ayesha.kamal@{EMAIL_DOMAIN}", True),
    ("DSG-AST-011", "Jabra Evolve2 40", "Headset", 28000, f"saima.riaz@{EMAIL_DOMAIN}", False),
    ("DSG-AST-012", "Jabra Evolve2 40", "Headset", 28000, f"hira.malik@{EMAIL_DOMAIN}", True),
    ("DSG-AST-013", "HQ Access Card", "Access Card", 2500, f"farah.aziz@{EMAIL_DOMAIN}", False),
    ("DSG-AST-014", "HQ Access Card", "Access Card", 2500, f"rehan.malik@{EMAIL_DOMAIN}", False),
    ("DSG-AST-015", "MacBook Air 13", "Laptop", 275000, f"lubna.sheikh@{EMAIL_DOMAIN}", False),
    ("DSG-AST-016", "MacBook Air 13", "Laptop", 275000, f"kashif.anwar@{EMAIL_DOMAIN}", True),
    ("DSG-AST-017", "iPhone 15", "Mobile Phone", 285000, CEO_EMAIL, False),
    ("DSG-AST-018", "Dell 27 Monitor", "Monitor", 65000, f"hamza.sheikh@{EMAIL_DOMAIN}", False),
)

# referral_source "linkedin" is not a valid choice; map in candidate create.
REFERRAL_MAP = {
    "linkedin": "social_media",
}


def _mgr(model):
    return getattr(model, "_base_manager", model.objects)


def _set_m2m(instance, field, values):
    getattr(instance, field).set(values)


class Command(BaseCommand):
    help = "Seed realistic employees, recruitments, and onboarding records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove previously seeded demo workforce records.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()
            return
        self._seed()

    def _clear(self):
        from asset.models import Asset, AssetAssignment, AssetItem
        from employee.models import Employee
        from onboarding.models import (
            CandidateStage,
            CandidateTask,
            OnboardingPortal,
            OnboardingStage,
            OnboardingTask,
        )
        from recruitment.models import (
            Candidate,
            CandidateRating,
            InterviewSchedule,
            Recruitment,
            SkillZoneCandidate,
            StageNote,
        )
        from horilla_auth.models import HorillaUser

        recs = _mgr(Recruitment).filter(title__startswith=TITLE_PREFIX)
        cands = _mgr(Candidate).filter(recruitment_id__in=recs)
        cand_ids = list(cands.values_list("pk", flat=True))
        rec_ids = list(recs.values_list("pk", flat=True))

        _mgr(InterviewSchedule).filter(candidate_id__in=cand_ids).delete()
        _mgr(CandidateRating).filter(candidate_id__in=cand_ids).delete()
        _mgr(StageNote).filter(candidate_id__in=cand_ids).delete()
        _mgr(SkillZoneCandidate).filter(candidate_id__in=cand_ids).delete()
        _mgr(OnboardingPortal).filter(candidate_id__in=cand_ids).delete()
        _mgr(CandidateTask).filter(candidate_id__in=cand_ids).delete()
        _mgr(CandidateStage).filter(candidate_id__in=cand_ids).delete()
        _mgr(OnboardingTask).filter(stage_id__recruitment_id__in=rec_ids).delete()
        cands.delete()
        rec_count = recs.count()
        recs.delete()

        assets = _mgr(Asset).filter(asset_tracking_id__startswith="DSG-AST-")
        asset_ids = list(assets.values_list("pk", flat=True))
        _mgr(AssetAssignment).filter(asset_id__in=asset_ids).delete()
        _mgr(AssetItem).filter(asset_id__in=asset_ids).delete()
        asset_count = assets.count()
        assets.delete()

        employees = _mgr(Employee).filter(email__iendswith=f"@{EMAIL_DOMAIN}")
        user_ids = list(
            employees.exclude(employee_user_id__isnull=True).values_list(
                "employee_user_id_id", flat=True
            )
        )
        emp_count = employees.count()
        employees.delete()
        if user_ids:
            HorillaUser.objects.filter(pk__in=user_ids).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {emp_count} employee(s), {rec_count} recruitment(s), "
                f"and {asset_count} asset(s)."
            )
        )

    @transaction.atomic
    def _seed(self):
        from base.models import Company, Department, EmployeeType, JobPosition, JobRole, WorkType
        from employee.models import Employee, EmployeeWorkInformation
        from horilla_auth.models import HorillaUser
        from onboarding.models import (
            CandidateStage,
            CandidateTask,
            OnboardingPortal,
            OnboardingStage,
            OnboardingTask,
        )
        from recruitment.models import (
            Candidate,
            CandidateRating,
            InterviewSchedule,
            Recruitment,
            RecruitmentGeneralSetting,
            RejectReason,
            RejectedCandidate,
            Skill,
            SkillZone,
            SkillZoneCandidate,
            Stage,
            StageNote,
        )

        company = _mgr(Company).order_by("id").first()
        if not company:
            raise CommandError("No company found. Create a company first.")

        work_type = self._ensure_named(
            WorkType, {"work_type": "Onsite"}, company, "company_id"
        )
        employee_type = self._ensure_named(
            EmployeeType, {"employee_type": "Full Time"}, company, "company_id"
        )

        org = self._ensure_org(company)
        employees = self._ensure_people(company, org, work_type, employee_type)
        self._attach_live_admin_root(employees)

        RecruitmentGeneralSetting._base_manager.update_or_create(
            company_id=company,
            defaults={"candidate_self_tracking": True, "show_overall_rating": True},
        )
        reject_skills, _ = RejectReason._base_manager.get_or_create(
            title="Skills gap",
            company_id=company,
            defaults={"description": "Does not meet the technical or role bar."},
        )
        reject_filled, _ = RejectReason._base_manager.get_or_create(
            title="Role filled",
            company_id=company,
            defaults={"description": "Another candidate was selected."},
        )

        talent_eng, _ = SkillZone._base_manager.get_or_create(
            title="Engineering talent pool",
            company_id=company,
            defaults={"description": "Strong engineering profiles to revisit."},
        )
        talent_hr, _ = SkillZone._base_manager.get_or_create(
            title="People team talent pool",
            company_id=company,
            defaults={"description": "HR and recruiting profiles."},
        )

        today = timezone.now().date()
        rec_count = 0
        cand_count = 0
        onboard_count = 0

        for spec in RECRUITMENTS:
            job = org["positions"][spec["job_position"]]
            managers = [employees[email] for email in spec["managers"] if email in employees]
            if not managers:
                managers = list(employees.values())[:2]

            recruitment, created = Recruitment._base_manager.get_or_create(
                title=spec["title"],
                defaults={
                    "description": spec["description"],
                    "is_event_based": False,
                    "closed": False,
                    "is_published": True,
                    "vacancy": spec["vacancy"],
                    "company_id": company,
                    "job_position_id": job,
                    "start_date": today - timedelta(days=spec["start_offset"]),
                    "end_date": today + timedelta(days=spec["end_offset"]),
                    "optional_profile_image": True,
                    "optional_resume": False,
                    "publish_in_linkedin": False,
                },
            )
            if not created:
                recruitment.vacancy = spec["vacancy"]
                recruitment.closed = False
                recruitment.is_published = True
                recruitment.job_position_id = job
                recruitment.company_id = company
                recruitment.publish_in_linkedin = False
                recruitment.save()

            recruitment.recruitment_managers.set(managers)
            recruitment.open_positions.set([job])
            skills = []
            for title in spec["skills"]:
                skill, _ = Skill._base_manager.get_or_create(title=title)
                skills.append(skill)
            recruitment.skills.set(skills)

            stage_by_type = self._ensure_recruit_stages(recruitment, managers)
            onboard_stages = self._ensure_onboard_stages(recruitment, managers)
            onboard_tasks = self._ensure_onboard_tasks(onboard_stages, managers)

            rec_count += 1
            rater = managers[0]
            hired_candidates = []

            for (
                name,
                stage_type,
                source,
                referral,
                gender,
                rating,
                onboard,
            ) in spec["candidates"]:
                email = self._candidate_email(name, spec["title"])
                stage = stage_by_type.get(stage_type) or stage_by_type["applied"]
                joining = today + timedelta(days=14) if stage_type == "hired" else None
                hired_on = today - timedelta(days=3) if stage_type == "hired" else None
                referral_source = REFERRAL_MAP.get(referral, referral)
                candidate, _ = Candidate._base_manager.update_or_create(
                    email=email,
                    recruitment_id=recruitment,
                    defaults={
                        "name": name,
                        "job_position_id": job,
                        "stage_id": stage,
                        "source": source,
                        "referral_source": referral_source,
                        "mobile": "03001119900",
                        "gender": gender,
                        "country": "Pakistan",
                        "city": "Karachi",
                        "address": "Clifton, Karachi",
                        "hired": stage_type == "hired",
                        "canceled": stage_type == "cancelled",
                        "start_onboard": bool(onboard),
                        "joining_date": joining,
                        "hired_date": hired_on,
                        "offer_letter_status": (
                            "accepted"
                            if stage_type == "hired"
                            else "sent"
                            if stage_type == "interview"
                            else "not_sent"
                        ),
                    },
                )
                if not candidate.resume:
                    candidate.resume.save(
                        f"{email.split('@')[0]}-resume.pdf",
                        ContentFile(MINIMAL_PDF),
                        save=True,
                    )
                cand_count += 1

                if rating is not None:
                    CandidateRating._base_manager.get_or_create(
                        candidate_id=candidate,
                        employee_id=rater,
                        defaults={"rating": rating},
                    )

                if stage_type == "interview":
                    interview, _ = InterviewSchedule._base_manager.get_or_create(
                        candidate_id=candidate,
                        interview_date=today + timedelta(days=2),
                        defaults={
                            "interview_time": time(11, 0),
                            "description": "Panel interview covering role fit and past work.",
                            "completed": False,
                        },
                    )
                    interview.employee_id.set(managers[:2])
                    StageNote._base_manager.get_or_create(
                        candidate_id=candidate,
                        stage_id=stage,
                        description=f"Shortlisted {name} for panel interview.",
                        defaults={"updated_by": rater, "candidate_can_view": False},
                    )

                if stage_type == "cancelled":
                    rejected, _ = RejectedCandidate._base_manager.get_or_create(
                        candidate_id=candidate,
                        defaults={
                            "description": "Not moving forward after screening.",
                        },
                    )
                    rejected.reject_reason_id.set([reject_skills])

                if stage_type == "hired":
                    StageNote._base_manager.get_or_create(
                        candidate_id=candidate,
                        stage_id=stage,
                        description=f"Offer accepted. Joining date {joining}.",
                        defaults={"updated_by": rater, "candidate_can_view": True},
                    )
                    if onboard:
                        hired_candidates.append(candidate)

                if stage_type in {"interview", "hired"} and "Engineer" in spec["title"]:
                    SkillZoneCandidate._base_manager.get_or_create(
                        skill_zone_id=talent_eng,
                        candidate_id=candidate,
                        defaults={"reason": "Strong technical background."},
                    )
                if stage_type in {"interview", "hired"} and "HR" in spec["title"]:
                    SkillZoneCandidate._base_manager.get_or_create(
                        skill_zone_id=talent_hr,
                        candidate_id=candidate,
                        defaults={"reason": "People operations experience."},
                    )

            for index, candidate in enumerate(hired_candidates):
                stage_titles = list(onboard_stages.keys())
                stage_title = stage_titles[min(index, len(stage_titles) - 1)]
                current_stage = onboard_stages[stage_title]
                CandidateStage._base_manager.update_or_create(
                    candidate_id=candidate,
                    defaults={
                        "onboarding_stage_id": current_stage,
                        "sequence": current_stage.sequence or 0,
                    },
                )
                OnboardingPortal._base_manager.get_or_create(
                    candidate_id=candidate,
                    defaults={
                        "token": f"demo-{candidate.pk}-{candidate.email.split('@')[0]}",
                        "used": index == 0,
                        "count": 1 if index == 0 else 0,
                    },
                )
                for task_stage_title, tasks in onboard_tasks.items():
                    task_stage = onboard_stages[task_stage_title]
                    for task in tasks:
                        task.candidates.add(candidate)
                        status = self._task_status(stage_title, task_stage_title, index)
                        CandidateTask._base_manager.get_or_create(
                            candidate_id=candidate,
                            onboarding_task_id=task,
                            stage_id=task_stage,
                            defaults={"status": status},
                        )
                onboard_count += 1

        asset_count, assigned_count, returned_count = self._ensure_assets(
            company, employees, today
        )

        self.stdout.write(self.style.SUCCESS("Demo workforce is ready."))
        self.stdout.write(f"  Company: {company}")
        self.stdout.write(f"  Employees: {len(employees)}")
        self.stdout.write(f"  Recruitments: {rec_count}")
        self.stdout.write(f"  Candidates: {cand_count}")
        self.stdout.write(f"  Onboarding: {onboard_count}")
        self.stdout.write(
            f"  Assets: {asset_count} ({assigned_count} currently assigned, "
            f"{returned_count} returned)"
        )
        self.stdout.write("")
        self.stdout.write(
            f"Employee logins use email + password: {DEFAULT_PASSWORD}"
        )
        self.stdout.write(
            "Examples: kamran.shah@demo.dsghrms.local, nadia.rahman@demo.dsghrms.local"
        )
        self.stdout.write(
            "Open Organization Chart, Recruitment → Pipeline, Onboarding → Pipeline, "
            "and Assets → History to review."
        )

    def _ensure_named(self, model, lookup, company, m2m_field):
        obj, _ = _mgr(model).get_or_create(**lookup)
        m2m = getattr(obj, m2m_field)
        if company.pk not in m2m.values_list("pk", flat=True):
            m2m.add(company)
        return obj

    def _ensure_org(self, company):
        from base.models import Department, JobPosition, JobRole

        departments = {}
        for name in DEPARTMENTS:
            dept, _ = _mgr(Department).get_or_create(department=name)
            if company.pk not in dept.company_id.values_list("pk", flat=True):
                dept.company_id.add(company)
            departments[name] = dept

        positions = {}
        roles = {}
        for dept_name, position_name, role_names in JOB_SETUP:
            dept = departments[dept_name]
            job, _ = _mgr(JobPosition).get_or_create(
                department_id=dept, job_position=position_name
            )
            if company.pk not in job.company_id.values_list("pk", flat=True):
                job.company_id.add(company)
            positions[position_name] = job
            for role_name in role_names:
                role, _ = _mgr(JobRole).get_or_create(
                    job_position_id=job, job_role=role_name
                )
                if company.pk not in role.company_id.values_list("pk", flat=True):
                    role.company_id.add(company)
                roles[(position_name, role_name)] = role
        return {"departments": departments, "positions": positions, "roles": roles}

    def _ensure_people(self, company, org, work_type, employee_type):
        from employee.models import Employee, EmployeeWorkInformation
        from horilla_auth.models import HorillaUser

        by_email = {}
        for person in PEOPLE:
            user = HorillaUser.objects.filter(username=person["email"]).first()
            if user is None:
                user = HorillaUser.objects.filter(email=person["email"]).first()
            if user is None:
                user = HorillaUser.objects.create_user(
                    username=person["email"],
                    email=person["email"],
                    password=DEFAULT_PASSWORD,
                    first_name=person["first_name"],
                    last_name=person["last_name"],
                    is_superuser=False,
                    is_staff=False,
                )
            else:
                user.set_password(DEFAULT_PASSWORD)
                user.first_name = person["first_name"]
                user.last_name = person["last_name"]
                user.is_active = True
                user.save()

            employee = _mgr(Employee).filter(email=person["email"]).first()
            defaults = {
                "employee_user_id": user,
                "employee_first_name": person["first_name"],
                "employee_last_name": person["last_name"],
                "phone": person["phone"],
                "badge_id": person["badge_id"],
                "gender": person["gender"],
                "dob": person["dob"],
                "city": person["city"],
                "country": "Pakistan",
                "state": "Sindh" if person["city"] == "Karachi" else "Punjab",
                "address": f"{person['city']}, Pakistan",
                "qualification": person["qualification"],
                "experience": person["experience"],
                "marital_status": person["marital_status"],
                "is_active": True,
            }
            if employee is None:
                employee = Employee(email=person["email"], **defaults)
                employee.save()
            else:
                for field, value in defaults.items():
                    setattr(employee, field, value)
                employee.save()
            by_email[person["email"]] = employee

        for person in PEOPLE:
            employee = by_email[person["email"]]
            manager = by_email.get(person["manager_email"]) if person["manager_email"] else None
            dept = org["departments"][person["department"]]
            job = org["positions"][person["job_position"]]
            role = org["roles"][(person["job_position"], person["job_role"])]
            work_info, _ = EmployeeWorkInformation.objects.get_or_create(
                employee_id=employee
            )
            work_info.company_id = company
            work_info.department_id = dept
            work_info.job_position_id = job
            work_info.job_role_id = role
            work_info.work_type_id = work_type
            work_info.employee_type_id = employee_type
            work_info.reporting_manager_id = manager
            work_info.date_joining = person["joining"]
            work_info.email = person["email"]
            work_info.mobile = person["phone"]
            work_info.location = f"{person['city']} HQ"
            work_info.basic_salary = person["salary"]
            work_info.experience = float(person["experience"])
            work_info.save()

        return by_email

    def _attach_live_admin_root(self, employees):
        """Hang the demo org chart under the real admin so it appears in their chart."""
        from employee.models import EmployeeWorkInformation
        from horilla_auth.models import HorillaUser

        ceo = employees.get(CEO_EMAIL)
        if not ceo:
            return
        admin = (
            HorillaUser.objects.filter(is_superuser=True, is_active=True)
            .exclude(email__iendswith=f"@{EMAIL_DOMAIN}")
            .order_by("id")
            .first()
        )
        boss = getattr(admin, "employee_get", None) if admin else None
        if not boss:
            return
        work_info = EmployeeWorkInformation.objects.filter(employee_id=ceo).first()
        if not work_info:
            return
        work_info.reporting_manager_id = boss
        work_info.save(update_fields=["reporting_manager_id"])

    def _ensure_recruit_stages(self, recruitment, managers):
        from recruitment.models import Stage

        by_type = {}
        for title, stage_type, sequence in RECRUIT_STAGES:
            stage = (
                Stage._base_manager.filter(
                    recruitment_id=recruitment, stage_type=stage_type
                ).first()
                or Stage._base_manager.filter(
                    recruitment_id=recruitment, stage=title
                ).first()
            )
            if stage is None:
                stage = Stage._base_manager.create(
                    recruitment_id=recruitment,
                    stage=title,
                    stage_type=stage_type,
                    sequence=sequence,
                )
            else:
                stage.stage = title
                stage.stage_type = stage_type
                stage.sequence = sequence
                stage.save(update_fields=["stage", "stage_type", "sequence"])
            stage.stage_managers.set(managers)
            by_type[stage_type] = stage
        return by_type

    def _ensure_onboard_stages(self, recruitment, managers):
        from onboarding.models import OnboardingStage

        by_title = {}
        existing = list(
            OnboardingStage._base_manager.filter(recruitment_id=recruitment).order_by(
                "sequence", "id"
            )
        )
        for index, (title, sequence, is_final) in enumerate(ONBOARD_STAGES):
            if index < len(existing):
                stage = existing[index]
                stage.stage_title = title
                stage.sequence = sequence
                stage.is_final_stage = is_final
                stage.save(update_fields=["stage_title", "sequence", "is_final_stage"])
            else:
                stage = OnboardingStage._base_manager.create(
                    recruitment_id=recruitment,
                    stage_title=title,
                    sequence=sequence,
                    is_final_stage=is_final,
                )
            stage.employee_id.set(managers)
            by_title[title] = stage
        return by_title

    def _ensure_onboard_tasks(self, onboard_stages, managers):
        from onboarding.models import OnboardingTask

        by_stage = {}
        for stage_title, task_defs in ONBOARD_TASKS.items():
            stage = onboard_stages[stage_title]
            tasks = []
            for task_title, required in task_defs:
                task, _ = OnboardingTask._base_manager.get_or_create(
                    stage_id=stage,
                    task_title=task_title,
                    defaults={"is_required": required},
                )
                if task.is_required != required:
                    task.is_required = required
                    task.save(update_fields=["is_required"])
                task.employee_id.set(managers)
                tasks.append(task)
            by_stage[stage_title] = tasks
        return by_stage

    def _ensure_assets(self, company, employees, today):
        from asset.models import Asset, AssetAssignment, AssetCategory, AssetItem, AssetLot

        assigner = (
            employees.get(f"hamza.sheikh@{EMAIL_DOMAIN}")
            or employees.get(CEO_EMAIL)
            or next(iter(employees.values()))
        )
        categories = {}
        for name, description in ASSET_CATEGORIES:
            category, _ = AssetCategory._base_manager.get_or_create(
                asset_category_name=name,
                defaults={"asset_category_description": description},
            )
            if company.pk not in category.company_id.values_list("pk", flat=True):
                category.company_id.add(company)
            categories[name] = category

        lot, _ = AssetLot._base_manager.get_or_create(
            lot_number="DSG-2026-IT",
            defaults={"lot_description": "2026 IT hardware batch for DSG HQ."},
        )
        if company.pk not in lot.company_id.values_list("pk", flat=True):
            lot.company_id.add(company)

        assigned_count = 0
        returned_count = 0
        for serial, name, category_name, cost, assignee_email, returned in ASSET_RECORDS:
            assignee = employees.get(assignee_email)
            if not assignee:
                continue
            asset, created = Asset._base_manager.get_or_create(
                asset_tracking_id=serial,
                defaults={
                    "asset_name": name,
                    "asset_description": f"Demo {name} issued from the 2026 IT batch.",
                    "asset_purchase_date": today - timedelta(days=180),
                    "asset_purchase_cost": cost,
                    "asset_category_id": categories[category_name],
                    "asset_status": "Available" if returned else "In use",
                    "asset_lot_number_id": lot,
                    "quantity": 1,
                    "expiry_date": today + timedelta(days=365),
                    "owner": None if returned else assignee,
                },
            )
            if not created:
                asset.asset_name = name
                asset.asset_category_id = categories[category_name]
                asset.asset_lot_number_id = lot
                asset.asset_purchase_cost = cost
                asset.quantity = 1
                asset.owner = None if returned else assignee
                asset.asset_status = "Available" if returned else "In use"
                asset.save()

            item, _ = AssetItem._base_manager.get_or_create(
                tracking_id=serial,
                defaults={
                    "asset_id": asset,
                    "status": "Available" if returned else "In use",
                },
            )
            if item.asset_id_id != asset.pk or item.status != (
                "Available" if returned else "In use"
            ):
                item.asset_id = asset
                item.status = "Available" if returned else "In use"
                item.save()

            assignment = (
                AssetAssignment._base_manager.filter(
                    asset_id=asset, assigned_to_employee_id=assignee
                )
                .order_by("id")
                .first()
            )
            assigned_on = today - timedelta(days=90 if returned else 40)
            returned_on = today - timedelta(days=12) if returned else None
            if assignment is None:
                assignment = AssetAssignment._base_manager.create(
                    asset_id=asset,
                    asset_item_id=item,
                    assigned_to_employee_id=assignee,
                    assigned_by_employee_id=assigner,
                    return_date=returned_on,
                    return_condition=(
                        "Returned in working condition after role change."
                        if returned
                        else ""
                    ),
                    return_status="Healthy" if returned else None,
                    return_request=False,
                )
            else:
                assignment.asset_item_id = item
                assignment.assigned_by_employee_id = assigner
                assignment.return_date = returned_on
                assignment.return_condition = (
                    "Returned in working condition after role change."
                    if returned
                    else ""
                )
                assignment.return_status = "Healthy" if returned else None
                assignment.save()
            AssetAssignment._base_manager.filter(pk=assignment.pk).update(
                assigned_date=assigned_on,
                return_date=returned_on,
            )
            if returned:
                returned_count += 1
            else:
                assigned_count += 1

        return len(ASSET_RECORDS), assigned_count, returned_count

    def _candidate_email(self, name, recruitment_title):
        slug = name.lower().replace(" ", ".")
        rec_slug = (
            recruitment_title.replace(TITLE_PREFIX, "")
            .strip()
            .lower()
            .replace(" ", "-")[:24]
        )
        return f"{slug}.{rec_slug}@{EMAIL_DOMAIN}"

    def _task_status(self, current_title, task_stage_title, index):
        titles = [item[0] for item in ONBOARD_STAGES]
        current_idx = titles.index(current_title)
        task_idx = titles.index(task_stage_title)
        if task_idx < current_idx:
            return "done"
        if task_idx == current_idx:
            if index % 2 == 0:
                return "ongoing"
            return "todo"
        return "todo"
