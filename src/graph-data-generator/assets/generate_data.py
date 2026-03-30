#!/usr/bin/env python3
"""
Graph Fake Data Generator

Reads a graph schema (arrows.app JSON format) and generates realistic fake data
using the Faker library. Outputs CSV files per node label and per relationship type.

Usage:
    python generate_data.py schema.json --output-dir ./data --scale 1000

The schema JSON is the arrows.app export format:
{
  "graph": {
    "nodes": [{ "id": "n0", "caption": "Person", "labels": ["Person"],
                "properties": { "name": "string", "age": "integer" }, ... }],
    "relationships": [{ "id": "r0", "type": "KNOWS", "fromId": "n0", "toId": "n1",
                         "properties": { "since": "date" } }]
  }
}
"""

import argparse
import csv
import json
import math
import os
import random
import sys
from datetime import datetime, timedelta

try:
    from faker import Faker
except ImportError:
    print("ERROR: Faker is not installed. Run: pip install faker --break-system-packages")
    sys.exit(1)

fake = Faker()
Faker.seed(42)
random.seed(42)

# ── Type-to-Faker mapping ──────────────────────────────────────────────────────
# Maps property names and types to appropriate Faker generators.
# We check property name first (more specific), then fall back to type.

NAME_GENERATORS = {
    # Identity
    "name": lambda: fake.name(),
    "fullname": lambda: fake.name(),
    "full_name": lambda: fake.name(),
    "firstname": lambda: fake.first_name(),
    "first_name": lambda: fake.first_name(),
    "lastname": lambda: fake.last_name(),
    "last_name": lambda: fake.last_name(),
    "username": lambda: fake.user_name(),
    "user_name": lambda: fake.user_name(),

    # Contact
    "email": lambda: fake.unique.email(),
    "phone": lambda: fake.phone_number(),
    "phonenumber": lambda: fake.phone_number(),
    "phone_number": lambda: fake.phone_number(),

    # Location
    "address": lambda: fake.address().replace("\n", ", "),
    "street": lambda: fake.street_address(),
    "city": lambda: fake.city(),
    "state": lambda: fake.state(),
    "country": lambda: fake.country(),
    "zipcode": lambda: fake.zipcode(),
    "zip_code": lambda: fake.zipcode(),
    "zip": lambda: fake.zipcode(),
    "latitude": lambda: str(fake.latitude()),
    "longitude": lambda: str(fake.longitude()),
    "lat": lambda: str(fake.latitude()),
    "lng": lambda: str(fake.longitude()),
    "lon": lambda: str(fake.longitude()),

    # Business
    "company": lambda: fake.company(),
    "companyname": lambda: fake.company(),
    "company_name": lambda: fake.company(),
    "jobtitle": lambda: fake.job(),
    "job_title": lambda: fake.job(),
    "job": lambda: fake.job(),
    "industry": lambda: fake.bs(),
    "department": lambda: random.choice(["Engineering", "Marketing", "Sales", "HR", "Finance", "Support", "Legal", "Operations", "Product", "Design"]),

    # Product / Commerce
    "price": lambda: round(random.uniform(1.0, 999.99), 2),
    "amount": lambda: round(random.uniform(1.0, 10000.0), 2),
    "total": lambda: round(random.uniform(10.0, 5000.0), 2),
    "cost": lambda: round(random.uniform(1.0, 500.0), 2),
    "quantity": lambda: random.randint(1, 100),
    "qty": lambda: random.randint(1, 100),
    "sku": lambda: fake.bothify("???-#####").upper(),
    "currency": lambda: fake.currency_code(),
    "productname": lambda: fake.catch_phrase(),
    "product_name": lambda: fake.catch_phrase(),

    # Content
    "title": lambda: fake.sentence(nb_words=random.randint(3, 8)).rstrip("."),
    "description": lambda: fake.paragraph(nb_sentences=2),
    "summary": lambda: fake.paragraph(nb_sentences=1),
    "body": lambda: fake.paragraph(nb_sentences=4),
    "content": lambda: fake.paragraph(nb_sentences=3),
    "text": lambda: fake.sentence(),
    "comment": lambda: fake.sentence(),
    "bio": lambda: fake.paragraph(nb_sentences=2),
    "tagline": lambda: fake.catch_phrase(),
    "category": lambda: random.choice(["Electronics", "Clothing", "Books", "Home", "Sports", "Toys", "Food", "Health", "Auto", "Garden"]),
    "tag": lambda: fake.word(),
    "genre": lambda: random.choice(["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller", "Documentary", "Animation", "Fantasy"]),
    "type": lambda: fake.word(),
    "status": lambda: random.choice(["active", "inactive", "pending", "completed", "cancelled"]),
    "priority": lambda: random.choice(["low", "medium", "high", "critical"]),
    "level": lambda: random.choice(["beginner", "intermediate", "advanced", "expert"]),

    # Web
    "url": lambda: fake.url(),
    "website": lambda: fake.url(),
    "image": lambda: fake.image_url(),
    "imageurl": lambda: fake.image_url(),
    "image_url": lambda: fake.image_url(),
    "avatar": lambda: fake.image_url(),
    "ip": lambda: fake.ipv4(),
    "ipaddress": lambda: fake.ipv4(),
    "ip_address": lambda: fake.ipv4(),
    "useragent": lambda: fake.user_agent(),

    # Identifiers
    "id": lambda: fake.uuid4(),
    "uuid": lambda: fake.uuid4(),

    # Dates
    "date": lambda: fake.date_between(start_date="-5y", end_date="today").isoformat(),
    "createdat": lambda: fake.date_time_between(start_date="-3y", end_date="now").isoformat(),
    "created_at": lambda: fake.date_time_between(start_date="-3y", end_date="now").isoformat(),
    "updatedat": lambda: fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
    "updated_at": lambda: fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
    "birthday": lambda: fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
    "dob": lambda: fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
    "date_of_birth": lambda: fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
    "since": lambda: fake.date_between(start_date="-10y", end_date="today").isoformat(),
    "timestamp": lambda: fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
    "startedat": lambda: fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
    "started_at": lambda: fake.date_time_between(start_date="-2y", end_date="now").isoformat(),

    # Numeric
    "age": lambda: random.randint(18, 85),
    "rating": lambda: round(random.uniform(1.0, 5.0), 1),
    "score": lambda: random.randint(0, 100),
    "count": lambda: random.randint(0, 10000),
    "weight": lambda: round(random.uniform(0.1, 100.0), 2),
    "height": lambda: round(random.uniform(140.0, 210.0), 1),
    "duration": lambda: random.randint(1, 480),
    "year": lambda: random.randint(1950, 2026),
    "released": lambda: random.randint(1970, 2026),
    "runtime": lambda: random.randint(60, 240),

    # Boolean
    "active": lambda: random.choice([True, False]),
    "verified": lambda: random.choice([True, False]),
    "published": lambda: random.choice([True, False]),
    "featured": lambda: random.choice([True, False]),
    "adult": lambda: random.choice([True, False]),
    "available": lambda: random.choice([True, False]),
    "isfraud": lambda: random.choice([True, False]),
    "iscurrent": lambda: random.choice([True, False]),

    # Domain-specific identifiers
    "vin": lambda: fake.bothify("?####??#?##??????").upper(),
    "passportnumber": lambda: fake.bothify("#########"),
    "passport_number": lambda: fake.bothify("#########"),
    "licensenumber": lambda: fake.bothify("??###########").upper(),
    "license_number": lambda: fake.bothify("??###########").upper(),
    "claimid": lambda: "CL" + fake.bothify("####"),
    "policyid": lambda: "POL" + fake.bothify("######"),
    "policynumber": lambda: "POL" + fake.bothify("######"),
    "policy_number": lambda: "POL" + fake.bothify("######"),
    "accountnumber": lambda: fake.bothify("ACC####"),
    "account_number": lambda: fake.bothify("ACC####"),
    "transactionid": lambda: "TXN" + fake.bothify("######"),
    "transaction_id": lambda: "TXN" + fake.bothify("######"),
    "sessionid": lambda: "SESS" + fake.bothify("######"),
    "deviceid": lambda: "DEV" + fake.uuid4()[:8],
    "faceid": lambda: "FACE" + fake.bothify("####"),
    "counterpartyid": lambda: "CP" + fake.bothify("####"),
    "movementid": lambda: "MOV" + fake.bothify("####"),
    "alertid": lambda: "ALERT" + fake.bothify("####"),
    "caseid": lambda: "CASE" + fake.bothify("####"),
    "patentid": lambda: fake.bothify("US########"),
    "trialid": lambda: "NCT" + fake.bothify("########"),
    "cveid": lambda: "CVE-" + str(random.randint(2019,2026)) + "-" + str(random.randint(1000,99999)),
    "cvssscore": lambda: round(random.uniform(0.0, 10.0), 1),
    "severity": lambda: random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    "ecosystem": lambda: random.choice(["npm", "pypi", "maven", "nuget", "crates.io", "rubygems"]),
    "spdxid": lambda: random.choice(["MIT", "Apache-2.0", "GPL-3.0", "BSD-2-Clause", "ISC", "MPL-2.0"]),
    "cpe": lambda: "cpe:2.3:a:" + fake.word() + ":" + fake.word() + ":" + str(random.randint(1,20)) + "." + str(random.randint(0,9)),
    "impactfactor": lambda: round(random.uniform(0.5, 50.0), 2),
    "hindex": lambda: random.randint(1, 100),
    "doi": lambda: "10." + str(random.randint(1000,9999)) + "/" + fake.bothify("???.####"),
    "isin": lambda: random.choice(["US","GB","DE","FR","JP"]) + fake.bothify("##########"),
    "symbol": lambda: fake.bothify("????").upper(),
    "pct": lambda: round(random.uniform(0.1, 15.0), 2),

    # Medical
    "dosage": lambda: random.choice(["10mg", "25mg", "50mg", "100mg", "250mg", "500mg"]),
    "birthdate": lambda: fake.date_of_birth(minimum_age=18, maximum_age=85).isoformat(),

    # Manufacturing
    "power_kw": lambda: random.choice([50, 100, 150, 200, 250, 350]),
    "powerkw": lambda: random.choice([50, 100, 150, 200, 250, 350]),
    "battery_capacity_kwh": lambda: random.choice([40, 56, 75, 82, 100]),
    "efficiency_kwh_per_km": lambda: round(random.uniform(0.05, 0.25), 2),
    "current_soc_percent": lambda: random.randint(10, 95),
    "distance_km": lambda: round(random.uniform(5.0, 500.0), 1),
    "speed_limit_kph": lambda: random.choice([50, 60, 80, 100, 110, 130]),
    "connectortype": lambda: random.choice(["Type 2", "CCS", "CHAdeMO", "Tesla"]),
    "connector_type": lambda: random.choice(["Type 2", "CCS", "CHAdeMO", "Tesla"]),
    "completion_progress": lambda: round(random.uniform(0.0, 1.0), 2),
    "quality_score": lambda: round(random.uniform(0.0, 1.0), 2),

    # Security / IAM
    "privilegelevel": lambda: random.choice(["user", "admin", "service_account", "root"]),
    "privilege_level": lambda: random.choice(["user", "admin", "service_account", "root"]),
    "scope": lambda: random.choice(["read", "write", "admin", "full_access", "read_only"]),
    "zone": lambda: random.choice(["dmz", "internal", "production", "staging", "management"]),
    "tier": lambda: random.choice(["P0", "P1", "P2", "P3"]),
    "strength": lambda: random.choice(["weak", "medium", "strong"]),
    "method": lambda: random.choice(["email", "phone_number", "sms", "biometric", "password", "mfa"]),

    # Financial
    "riskrating": lambda: random.choice(["LOW", "MEDIUM", "HIGH"]),
    "risk_rating": lambda: random.choice(["LOW", "MEDIUM", "HIGH"]),
    "risklevel": lambda: random.choice(["LOW", "MEDIUM", "HIGH"]),
    "amountclaimed": lambda: round(random.uniform(500.0, 50000.0), 2),
    "amount_claimed": lambda: round(random.uniform(500.0, 50000.0), 2),
    "balance": lambda: round(random.uniform(100.0, 100000.0), 2),
    "interestrate": lambda: round(random.uniform(0.5, 8.0), 2),
    "interest_rate": lambda: round(random.uniform(0.5, 8.0), 2),
    "premium": lambda: round(random.uniform(50.0, 5000.0), 2),
    "financialstakes": lambda: round(random.uniform(1000.0, 500000.0), 2),
    "role": lambda: random.choice(["OWNER", "joint", "authorised_signatory"]),
    "accounttype": lambda: random.choice(["CURRENT", "SAVINGS", "BUSINESS", "LOAN"]),
    "account_type": lambda: random.choice(["CURRENT", "SAVINGS", "BUSINESS", "LOAN"]),
    "message": lambda: random.choice(["Payment for services", "Invoice payment", "Transfer", "Refund", "Salary", "Insurance claim"]),
    "outcome": lambda: random.choice(["PROVEN_FRAUD", "NOT_FRAUD", "FRAUD_UNPROVABLE", "UNDER_REVIEW"]),

    # Geography / Country
    "code": lambda: random.choice(["US", "GB", "DE", "FR", "JP", "AU", "CA", "CH", "NL", "SG"]),
    "countrycode": lambda: random.choice(["+1", "+44", "+49", "+33", "+81", "+61"]),
    "country_code": lambda: random.choice(["+1", "+44", "+49", "+33", "+81", "+61"]),
    "issuingcountry": lambda: random.choice(["US", "GB", "DE", "FR", "JP"]),
    "issuing_country": lambda: random.choice(["US", "GB", "DE", "FR", "JP"]),
    "postcode": lambda: fake.postcode(),
    "post_code": lambda: fake.postcode(),
    "region": lambda: fake.state(),
    "addressline1": lambda: fake.street_address(),
    "address_line_1": lambda: fake.street_address(),
    "addressline2": lambda: random.choice(["", "Flat " + str(random.randint(1,20)), "Suite " + str(random.randint(100,999)), "Unit " + str(random.randint(1,50))]),
    "posttown": lambda: fake.city(),
    "post_town": lambda: fake.city(),
    "domain": lambda: fake.domain_name(),
    "emaildomain": lambda: fake.free_email_domain(),
    "email_domain": lambda: fake.free_email_domain(),

    # Rule / Compliance
    "rulename": lambda: random.choice(["Large Transaction to High Risk Jurisdiction", "Unusual Transaction Pattern", "Rapid Account Changes", "Multiple Failed Logins", "Velocity Threshold Exceeded"]),
    "rule_name": lambda: random.choice(["Large Transaction to High Risk Jurisdiction", "Unusual Transaction Pattern", "Rapid Account Changes", "Multiple Failed Logins", "Velocity Threshold Exceeded"]),
    "ruleid": lambda: "RULE_" + fake.bothify("??_###").upper(),

    # Diff / Quote
    "diff_seconds": lambda: random.randint(5, 86400),
    "diffseconds": lambda: random.randint(5, 86400),
    "change_info": lambda: random.choice(["Changed postcode", "Changed firstname", "Changed dob", "Changed surname", "No change"]),
}

# ── Context-aware generators ─────────────────────────────────────────────────
# When the NODE LABEL provides context, override generic property generators.
# Format: { (normalized_label, normalized_prop): generator }
# This ensures a "name" on a Drug is a drug name, not a person name.

CONTEXT_GENERATORS = {
    # Healthcare
    ("drug", "name"): lambda: random.choice(["Aspirin", "Amoxicillin", "Metformin", "Lisinopril", "Atorvastatin", "Omeprazole", "Levothyroxine", "Amlodipine", "Simvastatin", "Losartan", "Gabapentin", "Sertraline", "Ibuprofen", "Prednisone", "Tramadol", "Warfarin", "Clopidogrel", "Insulin Glargine", "Paracetamol", "Doxycycline"]),
    ("drug", "code"): lambda: fake.bothify("ATC-?##??"),
    ("medication", "name"): lambda: random.choice(["Aspirin 100mg", "Metformin 500mg", "Amoxicillin 250mg", "Ibuprofen 400mg", "Omeprazole 20mg", "Paracetamol 500mg"]),
    ("condition", "description"): lambda: random.choice(["Type 2 Diabetes Mellitus", "Essential Hypertension", "Major Depressive Disorder", "Acute Bronchitis", "Osteoarthritis", "Chronic Kidney Disease", "Asthma", "GERD", "Migraine", "Anemia", "Hypothyroidism", "Atrial Fibrillation", "Pneumonia", "Urinary Tract Infection", "Anxiety Disorder"]),
    ("condition", "code"): lambda: random.choice(["E11", "I10", "F32", "J20", "M15", "N18", "J45", "K21", "G43", "D50", "E03", "I48", "J18", "N39", "F41"]),
    ("observation", "description"): lambda: random.choice(["Blood Pressure", "Heart Rate", "Body Temperature", "Respiratory Rate", "Blood Glucose", "BMI", "SpO2", "White Blood Cell Count", "Hemoglobin", "Cholesterol", "Creatinine", "Platelet Count"]),
    ("observation", "value"): lambda: random.choice(["120/80 mmHg", "72 bpm", "37.0°C", "16 breaths/min", "5.5 mmol/L", "24.5 kg/m²", "98%", "7.5 x10^9/L", "14.2 g/dL", "5.2 mmol/L", "88 µmol/L", "250 x10^9/L"]),
    ("speciality", "name"): lambda: random.choice(["Cardiology", "Neurology", "Oncology", "Pediatrics", "Orthopedics", "Dermatology", "Gastroenterology", "Pulmonology", "Nephrology", "Endocrinology", "Rheumatology", "Ophthalmology", "Psychiatry", "Emergency Medicine", "General Surgery"]),
    ("organisation", "name"): lambda: random.choice(["Royal London Hospital", "St. Mary's Hospital", "Johns Hopkins", "Mayo Clinic", "Cleveland Clinic", "Mount Sinai", "Massachusetts General", "Stanford Medical Center"]),
    ("provider", "name"): lambda: "Dr. " + fake.name(),
    ("patient", "name"): lambda: fake.name(),
    ("patient", "gender"): lambda: random.choice(["Male", "Female"]),
    ("encounter", "type"): lambda: random.choice(["inpatient", "outpatient", "emergency", "observation", "virtual"]),
    ("encounter", "description"): lambda: random.choice(["Routine checkup", "Follow-up visit", "Emergency admission", "Specialist referral", "Lab work review", "Surgery pre-op", "Post-op follow-up"]),

    # Pharma / Patents
    ("patent", "title"): lambda: random.choice(["Selective inhibitor of ", "Novel compound for treatment of ", "Method for modulating ", "Composition comprising ", "Antibody targeting "]) + random.choice(["BACE1", "PD-L1", "VEGF", "TNF-alpha", "JAK2", "EGFR", "BRCA1", "CDK4/6"]),
    ("owner", "name"): lambda: random.choice(["Pfizer Inc.", "Novartis AG", "Roche Holdings", "Johnson & Johnson", "AstraZeneca", "Merck & Co.", "AbbVie", "Sanofi", "Bayer AG", "GlaxoSmithKline"]),
    ("target", "name"): lambda: random.choice(["BACE1", "APOE", "TREM2", "MAPT", "PD-L1", "VEGFR2", "EGFR", "HER2", "BRCA1", "TP53", "JAK2", "CDK4"]),
    ("target", "function"): lambda: random.choice(["Beta-secretase enzyme", "Apolipoprotein E", "Immune receptor", "Microtubule-associated protein", "Immune checkpoint", "Tyrosine kinase receptor"]),
    ("disease", "name"): lambda: random.choice(["Alzheimer's Disease", "Breast Cancer", "Non-Small Cell Lung Cancer", "Rheumatoid Arthritis", "Multiple Sclerosis", "Type 2 Diabetes", "Parkinson's Disease", "Crohn's Disease"]),
    ("drugclass", "name"): lambda: random.choice(["Beta-secretase Inhibitor", "Checkpoint Inhibitor", "Tyrosine Kinase Inhibitor", "CDK4/6 Inhibitor", "JAK Inhibitor", "TNF Blocker", "mAb"]),
    ("mechanismofaction", "name"): lambda: random.choice(["Enzyme Inhibition", "Receptor Blockade", "Immune Modulation", "Signal Transduction Inhibition", "Gene Silencing", "Antibody-Dependent Cytotoxicity"]),

    # Publications
    ("publication", "title"): lambda: fake.sentence(nb_words=random.randint(8, 15)).rstrip("."),
    ("author", "name"): lambda: fake.name(),
    ("institution", "name"): lambda: random.choice(["Harvard University", "MIT", "Stanford University", "Oxford University", "Cambridge University", "ETH Zurich", "University of Tokyo", "Karolinska Institute", "Max Planck Institute"]),
    ("journal", "name"): lambda: random.choice(["Nature", "Science", "Cell", "The Lancet", "NEJM", "JAMA", "Nature Medicine", "Nature Biotechnology", "PNAS", "BMJ", "PLoS ONE"]),

    # Biology / Omics
    ("gene", "symbol"): lambda: random.choice(["TP53", "BRCA1", "BRCA2", "EGFR", "BRAF", "KRAS", "PIK3CA", "PTEN", "APC", "RB1", "MYC", "ERBB2", "CDH1", "VHL", "AKT1"]),
    ("gene", "name"): lambda: random.choice(["Tumor Protein P53", "BRCA1 DNA Repair", "Epidermal Growth Factor Receptor", "B-Raf Proto-Oncogene", "Phosphatidylinositol-4,5-Bisphosphate 3-Kinase"]),
    ("gene", "chromosome"): lambda: random.choice(["1", "2", "3", "5", "7", "10", "11", "12", "13", "17", "19", "22", "X"]),
    ("protein", "name"): lambda: random.choice(["p53", "BRCA1", "EGFR", "HER2", "VEGF", "TNF-alpha", "Insulin", "Hemoglobin", "Actin", "Albumin", "Collagen"]),
    ("protein", "uniprotid"): lambda: fake.bothify("?#????").upper(),
    ("metabolite", "name"): lambda: random.choice(["Glucose", "Lactate", "Pyruvate", "Cholesterol", "Urea", "Creatinine", "Acetyl-CoA", "ATP", "NADH", "Glutamate"]),
    ("metabolite", "formula"): lambda: random.choice(["C6H12O6", "C3H6O3", "C3H4O3", "C27H46O", "CH4N2O", "C4H7N3O", "C23H38N7O17P3S"]),
    ("pathway", "name"): lambda: random.choice(["Glycolysis", "TCA Cycle", "Oxidative Phosphorylation", "Pentose Phosphate Pathway", "Fatty Acid Synthesis", "Apoptosis Signaling", "MAPK Cascade", "Wnt Signaling", "Notch Signaling"]),
    ("phenotype", "name"): lambda: random.choice(["Elevated blood pressure", "Insulin resistance", "Chronic inflammation", "Impaired cognition", "Tumor growth", "Immune suppression"]),
    ("organism", "name"): lambda: random.choice(["Homo sapiens", "Mus musculus", "Rattus norvegicus", "Drosophila melanogaster", "Caenorhabditis elegans", "Danio rerio"]),

    # Insurance
    ("claimant", "name"): lambda: fake.name(),
    ("medicalprofessional", "name"): lambda: "Dr. " + fake.name(),
    ("vehicle", "vin"): lambda: fake.bothify("?####??#?##??????").upper(),
    ("claim", "type"): lambda: random.choice(["motor", "property", "liability", "health", "travel"]),
    ("broker", "name"): lambda: fake.company() + " Insurance",
    ("applicant", "name"): lambda: fake.name(),
    ("quote", "change_info"): lambda: random.choice(["Changed postcode", "Changed firstname", "Changed dob", "Changed surname", "No change"]),

    # Manufacturing
    ("machine", "name"): lambda: random.choice(["AssemblyMachine", "CNCMill", "LaserCutter", "RoboticArm", "ConveyorBelt", "PaintBooth", "WeldingStation", "PackagingUnit"]) + str(random.randint(1,20)),
    ("job", "name"): lambda: random.choice(["MaterialPrep", "Assembly", "QualityCheck", "Packaging", "Painting", "Welding", "Machining", "Inspection", "Testing"]) + "_" + fake.bothify("??##"),
    ("job", "status"): lambda: random.choice(["Completed", "Running", "Pending", "Failed"]),
    ("process", "name"): lambda: random.choice(["WidgetProduction", "GadgetProduction", "ComponentProduction", "AssemblyLine"]) + "_" + random.choice(["Q1", "Q2", "Q3", "Q4"]),
    ("product", "name"): lambda: random.choice(["Widget", "Gadget", "Component", "Module", "Assembly", "SubSystem"]) + " " + fake.bothify("??-####").upper(),
    ("configgroup", "category"): lambda: random.choice(["frame", "wheels", "engine", "suspension", "brakes", "electronics", "interior"]),
    ("configgroup", "name"): lambda: random.choice(["Frame Options", "Wheel Selection", "Engine Config", "Suspension Type", "Brake Package", "Electronics Suite"]),
    ("part", "name"): lambda: random.choice(["Steel Frame", "Carbon Frame", "Alloy Wheel", "LED Headlight", "Disc Brake", "Drum Brake", "Turbo Engine", "Electric Motor", "Air Filter", "Fuel Injector"]),
    ("part", "material"): lambda: random.choice(["Steel", "Aluminum", "Carbon Fiber", "Titanium", "Copper", "Plastic", "Rubber", "Glass"]),
    ("variant", "name"): lambda: random.choice(["Sport", "Comfort", "Eco", "Performance", "Standard", "Premium", "Lite", "Pro"]),
    ("city", "name"): lambda: fake.city(),
    ("chargingstation", "name"): lambda: "CS" + str(random.randint(1, 999)),
    ("car", "model"): lambda: random.choice(["Tesla Model 3", "Nissan Leaf", "BMW iX", "VW ID.4", "Hyundai Ioniq 5", "Rivian R1T", "Ford Mustang Mach-E"]),

    # Engineering Traceability
    ("customerrequest", "description"): lambda: "Customer " + random.choice(["needs", "requests", "requires", "wants"]) + " " + random.choice(["5G router with 10Gbps throughput", "low power consumption", "seamless handover", "remote diagnostics", "1ms latency", "ruggedized design"]),
    ("customerrequest", "source"): lambda: random.choice(["SFDC", "Email", "Call Center", "Partner Portal", "Direct"]),
    ("requirement", "description"): lambda: random.choice(["Support 5G NR Band", "Power consumption below 5W", "Latency under 1ms", "IP67 rated enclosure", "MIMO antenna support", "OTA firmware update"]),
    ("design", "description"): lambda: random.choice(["RF Frontend Module", "Power Management IC", "Baseband Processor", "Antenna Array Design", "Thermal Management System", "Enclosure Design"]),
    ("design", "version"): lambda: f"v{random.randint(1,5)}.{random.randint(0,9)}",
    ("testcase", "description"): lambda: random.choice(["Throughput test at max load", "Power consumption measurement", "Temperature cycling test", "EMC compliance test", "Latency benchmark", "Drop test"]),
    ("testcase", "status"): lambda: random.choice(["Passed", "Failed", "Pending", "In Progress"]),
    ("testcase", "result"): lambda: random.choice(["Pass", "Fail", "Conditional Pass", "Not Run"]),

    # Cybersecurity
    ("computeinstance", "hostname"): lambda: fake.hostname(),
    ("computeinstance", "os"): lambda: random.choice(["Ubuntu 22.04", "Amazon Linux 2", "Windows Server 2022", "RHEL 9", "CentOS 8", "Debian 12"]),
    ("computeinstance", "publicip"): lambda: fake.ipv4_public() if random.random() > 0.6 else "",
    ("application", "name"): lambda: random.choice(["web-api", "auth-service", "payment-gateway", "user-service", "analytics-engine", "notification-service", "data-pipeline", "admin-portal"]) + "-" + random.choice(["prod", "staging"]),
    ("library", "name"): lambda: random.choice(["log4j", "spring-core", "lodash", "express", "requests", "boto3", "jackson-databind", "commons-text", "numpy", "react", "django", "flask"]),
    ("library", "version"): lambda: f"{random.randint(1,5)}.{random.randint(0,30)}.{random.randint(0,15)}",
    ("cve", "description"): lambda: random.choice(["Remote code execution via ", "SQL injection in ", "Cross-site scripting in ", "Path traversal in ", "Deserialization vulnerability in ", "Buffer overflow in "]) + random.choice(["input validation", "authentication module", "file upload handler", "API endpoint", "XML parser", "session management"]),
    ("identity", "type"): lambda: random.choice(["IAM User", "Service Account", "IAM Role", "SSO User", "API Key"]),
    ("iampolicy", "name"): lambda: random.choice(["AdministratorAccess", "ReadOnlyAccess", "S3FullAccess", "EC2FullAccess", "LambdaExecute", "DatabaseAdmin", "NetworkAdmin"]),
    ("crownjewel", "name"): lambda: random.choice(["Customer PII Database", "Financial Records", "Source Code Repository", "Encryption Keys", "Authentication Service", "Payment System"]),
    ("crownjewel", "type"): lambda: random.choice(["Database", "S3 Bucket", "Service", "Secret Store", "Repository"]),
    ("cloudservice", "name"): lambda: random.choice(["S3 Bucket: customer-data", "RDS: prod-database", "Lambda: payment-processor", "EC2: web-frontend", "DynamoDB: session-store"]),
    ("cloudservice", "type"): lambda: random.choice(["S3", "RDS", "Lambda", "EC2", "DynamoDB", "EKS", "SQS"]),
    ("credential", "type"): lambda: random.choice(["password", "ssh_key", "api_token", "certificate", "kerberos_ticket"]),
    ("networksegment", "name"): lambda: random.choice(["DMZ", "Corporate LAN", "Production VPC", "Management Network", "Guest WiFi", "Database Subnet"]),
    ("vendor", "name"): lambda: random.choice(["Apache Foundation", "Google", "Microsoft", "Meta", "Amazon", "Red Hat", "Elastic", "HashiCorp", "Datadog", "Cloudflare"]),
    ("cisakev", "dateadded"): lambda: fake.date_between(start_date="-2y", end_date="today").isoformat(),

    # Regulatory
    ("standard", "id"): lambda: random.choice(["MIFIDPRU", "BCBS239", "SOX", "GDPR", "PCI-DSS", "ISO27001", "DORA", "Basel III"]),
    ("section", "title"): lambda: random.choice(["Application and purpose", "Scope of regulation", "Capital requirements", "Risk management", "Reporting obligations", "Governance arrangements"]),

    # Fund / Investment
    ("fund", "name"): lambda: random.choice(["Fundsmith Equity", "Lindsell Train Global", "Baillie Gifford", "Vanguard LifeStrategy", "BlackRock World"]) + " " + random.choice(["I Acc", "II Inc", "III Acc"]),
    ("stock", "name"): lambda: random.choice(["Microsoft Corporation", "Apple Inc.", "Novo Nordisk", "ASML Holdings", "LVMH", "Samsung Electronics", "Toyota Motor", "Nestle SA", "L'Oréal SA"]),
    ("stock", "symbol"): lambda: random.choice(["MSFT", "AAPL", "NOVO-B", "ASML", "MC.PA", "005930.KS", "7203.T", "NESN.SW", "OR.PA"]),
    ("holdings", "dummy"): lambda: "",

    # Financial - types
    ("transaction", "type"): lambda: random.choice(["SWIFT", "ACH", "FASTER_PAYMENT", "CARD", "WIRE", "DIRECT_DEBIT"]),
    ("transaction", "message"): lambda: random.choice(["Payment for services", "Invoice #" + fake.bothify("####"), "Salary payment", "Insurance claim", "Refund", "Transfer to savings"]),
    ("account", "accounttype"): lambda: random.choice(["CURRENT", "SAVINGS", "BUSINESS", "LOAN"]),
    ("counterparty", "type"): lambda: random.choice(["INDIVIDUAL", "BUSINESS", "GOVERNMENT", "CHARITY"]),
    ("country", "name"): lambda: fake.country(),
    ("country", "code"): lambda: random.choice(["US", "GB", "DE", "FR", "JP", "AU", "CA", "CH", "NL", "SG", "IE", "HK"]),
    ("isp", "name"): lambda: random.choice(["BT", "Virgin Media", "Comcast", "AT&T", "Deutsche Telekom", "NTT", "Vodafone", "Orange"]),
}

TYPE_GENERATORS = {
    "string": lambda: fake.word(),
    "str": lambda: fake.word(),
    "text": lambda: fake.sentence(),
    "integer": lambda: random.randint(1, 10000),
    "int": lambda: random.randint(1, 10000),
    "long": lambda: random.randint(1, 1000000),
    "float": lambda: round(random.uniform(0.0, 1000.0), 2),
    "double": lambda: round(random.uniform(0.0, 1000.0), 4),
    "number": lambda: round(random.uniform(0.0, 1000.0), 2),
    "boolean": lambda: random.choice([True, False]),
    "bool": lambda: random.choice([True, False]),
    "date": lambda: fake.date_between(start_date="-5y", end_date="today").isoformat(),
    "datetime": lambda: fake.date_time_between(start_date="-3y", end_date="now").isoformat(),
    "timestamp": lambda: fake.date_time_between(start_date="-3y", end_date="now").isoformat(),
    "email": lambda: fake.unique.email(),
    "url": lambda: fake.url(),
    "uuid": lambda: fake.uuid4(),
    "phone": lambda: fake.phone_number(),
}


def get_generator(prop_name, prop_type, node_label=""):
    """Return a generator function for a property based on name, type, and node context."""
    key = prop_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    key_under = prop_name.lower().strip()
    label_key = node_label.lower().replace(" ", "").replace("-", "").replace("_", "") if node_label else ""

    # Check context-aware generators first (label + property combo)
    if label_key and key in [k[1] for k in CONTEXT_GENERATORS if k[0] == label_key]:
        ctx_key = (label_key, key)
        if ctx_key in CONTEXT_GENERATORS:
            return CONTEXT_GENERATORS[ctx_key]
    # Also try with underscored key
    if label_key and key_under in [k[1] for k in CONTEXT_GENERATORS if k[0] == label_key]:
        ctx_key = (label_key, key_under)
        if ctx_key in CONTEXT_GENERATORS:
            return CONTEXT_GENERATORS[ctx_key]

    # Check name-based generators
    if key in NAME_GENERATORS:
        return NAME_GENERATORS[key]
    if key_under in NAME_GENERATORS:
        return NAME_GENERATORS[key_under]

    # Check for ID-suffix patterns (e.g. "customerId", "orderId")
    if key.endswith("id"):
        return lambda: fake.uuid4()

    # Fall back to type-based
    type_lower = prop_type.lower().strip() if prop_type else "string"
    if type_lower in TYPE_GENERATORS:
        return TYPE_GENERATORS[type_lower]

    return TYPE_GENERATORS["string"]


def compute_node_counts(schema, base_scale):
    """
    Compute how many nodes to generate per label.
    Uses relationship topology to infer relative sizes.
    The node with the most outgoing relationships gets base_scale;
    others are scaled relative to connectivity.
    """
    nodes = schema.get("nodes", [])
    relationships = schema.get("relationships", [])

    if not nodes:
        return {}

    # Count relationships per node to infer relative importance
    rel_count = {}
    for n in nodes:
        rel_count[n["id"]] = 0
    for r in relationships:
        rel_count.setdefault(r["fromId"], 0)
        rel_count.setdefault(r["toId"], 0)
        rel_count[r["fromId"]] += 1
        rel_count[r["toId"]] += 1

    # Heuristic: "leaf" nodes (fewer connections) get fewer instances,
    # "hub" nodes get the base scale
    max_rels = max(rel_count.values()) if rel_count else 1
    counts = {}
    for n in nodes:
        nid = n["id"]
        label = n["labels"][0] if n.get("labels") else n.get("caption", nid)
        connectivity = rel_count.get(nid, 0)
        # Scale: hubs get full scale, leaves get 20-50% of scale
        ratio = max(0.2, connectivity / max_rels) if max_rels > 0 else 1.0
        counts[nid] = {"label": label, "count": max(10, int(base_scale * ratio))}

    return counts


def generate_node_data(node_def, count):
    """Generate fake data rows for a node type."""
    props = node_def.get("properties", {})
    label = node_def["labels"][0] if node_def.get("labels") else node_def.get("caption", "Node")

    # Always include a unique _id column
    generators = {"_id": lambda i=None: fake.uuid4()}
    for prop_name, prop_type in props.items():
        generators[prop_name] = get_generator(prop_name, prop_type, label)

    rows = []
    fake.unique.clear()
    for i in range(count):
        row = {}
        for col, gen in generators.items():
            try:
                row[col] = gen()
            except Exception:
                row[col] = f"{col}_{i}"
        rows.append(row)

    return rows


def generate_relationship_data(rel_def, from_ids, to_ids, from_label, to_label, scale):
    """Generate fake relationship data connecting existing node IDs."""
    props = rel_def.get("properties", {})
    rel_type = rel_def.get("type", "RELATED_TO")
    is_self = rel_def["fromId"] == rel_def["toId"]

    generators = {}
    for prop_name, prop_type in props.items():
        generators[prop_name] = get_generator(prop_name, prop_type)

    # Determine number of relationships
    # Heuristic: ~2-5x the smaller node set, capped at scale
    num_rels = min(scale, max(len(from_ids), len(to_ids)) * random.randint(2, 5))
    num_rels = max(10, num_rels)

    rows = []
    seen = set()
    attempts = 0
    max_attempts = num_rels * 10

    while len(rows) < num_rels and attempts < max_attempts:
        attempts += 1
        from_id = random.choice(from_ids)
        to_id = random.choice(to_ids)

        # Avoid duplicate pairs (unless we run out of unique combos)
        pair_key = (from_id, to_id)
        if pair_key in seen and len(seen) < len(from_ids) * len(to_ids) * 0.8:
            continue
        seen.add(pair_key)

        row = {"_from_id": from_id, "_to_id": to_id}
        for col, gen in generators.items():
            try:
                row[col] = gen()
            except Exception:
                row[col] = f"{col}_{len(rows)}"
        rows.append(row)

    return rows


def write_csv(filepath, rows):
    """Write rows to a CSV file."""
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate fake graph data from a schema")
    parser.add_argument("schema", help="Path to arrows.app JSON schema file")
    parser.add_argument("--output-dir", "-o", default="./graph_data", help="Output directory for CSV files")
    parser.add_argument("--scale", "-s", type=int, default=1000, help="Base scale (number of nodes for the largest node type)")
    parser.add_argument("--summary", action="store_true", help="Print a summary of generated data")
    args = parser.parse_args()

    # Load schema
    with open(args.schema, "r") as f:
        raw = json.load(f)

    schema = raw.get("graph", raw)
    nodes = schema.get("nodes", [])
    relationships = schema.get("relationships", [])

    if not nodes:
        print("ERROR: No nodes found in schema.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Compute counts
    node_counts = compute_node_counts(schema, args.scale)

    print(f"📊 Generating data at scale={args.scale}")
    print(f"   Output: {os.path.abspath(args.output_dir)}\n")

    # Generate node data
    node_id_maps = {}  # node_def_id -> list of generated _id values
    for node_def in nodes:
        nid = node_def["id"]
        info = node_counts.get(nid, {"label": "Node", "count": args.scale})
        label = info["label"]
        count = info["count"]

        rows = generate_node_data(node_def, count)
        node_id_maps[nid] = [r["_id"] for r in rows]

        filename = f"nodes_{label.lower().replace(' ', '_')}.csv"
        filepath = os.path.join(args.output_dir, filename)
        write_csv(filepath, rows)
        print(f"   ✅ {label}: {count:,} nodes → {filename}")

    # Generate relationship data
    print()
    for rel_def in relationships:
        from_id = rel_def["fromId"]
        to_id = rel_def["toId"]
        rel_type = rel_def.get("type", "RELATED_TO")

        from_ids = node_id_maps.get(from_id, [])
        to_ids = node_id_maps.get(to_id, [])

        if not from_ids or not to_ids:
            print(f"   ⚠️  Skipping {rel_type}: missing node data for {from_id} or {to_id}")
            continue

        from_label = node_counts.get(from_id, {}).get("label", from_id)
        to_label = node_counts.get(to_id, {}).get("label", to_id)

        rows = generate_relationship_data(rel_def, from_ids, to_ids, from_label, to_label, args.scale)

        filename = f"rels_{rel_type.lower()}.csv"
        filepath = os.path.join(args.output_dir, filename)
        write_csv(filepath, rows)
        print(f"   ✅ {from_label} -[{rel_type}]-> {to_label}: {len(rows):,} relationships → {filename}")

    # Summary
    total_nodes = sum(len(ids) for ids in node_id_maps.values())
    total_rels = sum(1 for _ in relationships)
    print(f"\n🎉 Done! Generated {total_nodes:,} total nodes across {len(nodes)} labels")
    print(f"   Output directory: {os.path.abspath(args.output_dir)}")

    # Write a manifest for the ingestion skill to use
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "scale": args.scale,
        "schema": schema,
        "files": {
            "nodes": {},
            "relationships": {},
        }
    }
    for node_def in nodes:
        nid = node_def["id"]
        label = node_counts.get(nid, {}).get("label", "Node")
        manifest["files"]["nodes"][label] = {
            "file": f"nodes_{label.lower().replace(' ', '_')}.csv",
            "count": len(node_id_maps.get(nid, [])),
            "properties": node_def.get("properties", {}),
            "labels": node_def.get("labels", [label]),
        }
    for rel_def in relationships:
        rel_type = rel_def.get("type", "RELATED_TO")
        from_label = node_counts.get(rel_def["fromId"], {}).get("label", rel_def["fromId"])
        to_label = node_counts.get(rel_def["toId"], {}).get("label", rel_def["toId"])
        manifest["files"]["relationships"][rel_type] = {
            "file": f"rels_{rel_type.lower()}.csv",
            "from_label": from_label,
            "to_label": to_label,
            "properties": rel_def.get("properties", {}),
        }

    manifest_path = os.path.join(args.output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"   Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
