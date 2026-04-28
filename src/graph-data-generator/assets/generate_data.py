#!/usr/bin/env python3
"""
Graph Fake Data Generator

Reads a graph schema (arrows.app JSON format) and generates realistic fake data
using the Faker library. Outputs CSV files per node label and per relationship type.

Scale modes (auto-selected from --scale):
    < 100,000   → in-memory (fast, simple)
    ≥ 100,000   → streaming writes, ID indexes on disk
    ≥ 1,000,000 → chunked CSVs (nodes_Person_part1.csv, _part2.csv, …)

Usage:
    python generate_data.py schema.json \\
        --output-dir ./data \\
        --scale 10000 \\
        [--flavor generic|healthcare|finance|ecommerce|social] \\
        [--locale en_US] \\
        [--distribution powerlaw|uniform] \\
        [--seed 42]

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
import tempfile
import time

try:
    from faker import Faker
except ImportError:
    print("ERROR: Faker is not installed. Run: pip install faker", file=sys.stderr)
    sys.exit(1)

# ── Global Faker instance ─────────────────────────────────────────────────────
# Locale and seed are set in main() from CLI args. We initialise with defaults
# here so the generator tables below (which reference `fake` in lambdas) bind
# correctly at import time. main() replaces this instance before generation.
fake = Faker()
Faker.seed(42)
random.seed(42)

# ── Scale thresholds ──────────────────────────────────────────────────────────
STREAMING_THRESHOLD = 100_000     # ≥ this scale → stream to disk, don't hold in memory
CHUNK_THRESHOLD     = 1_000_000   # ≥ this scale → split CSVs into chunked parts
CHUNK_SIZE          = 500_000     # rows per chunked part file
PROGRESS_EVERY      = 100_000     # stderr progress update every N rows

# ── Flavor → Faker locale defaults ────────────────────────────────────────────
# Flavor is primarily a documentation aid: the CONTEXT_GENERATORS table below
# already dispatches domain-specific values from (label, property) pairs (e.g.
# a `name` on `Patient` becomes a patient name). Flavor sets a sensible default
# locale when --locale isn't provided explicitly.
FLAVOR_DEFAULT_LOCALE = {
    "generic":    "en_US",
    "healthcare": "en_US",
    "finance":    "en_US",
    "ecommerce":  "en_US",
    "social":     "en_US",
}

# ── Email uniqueness strategy ────────────────────────────────────────────────
# fake.unique.email() is the single biggest bottleneck in this script. It
# memoises every email it's ever returned and retries on collision — the
# retry cost grows quadratically as the set fills up. At 1M rows the
# generator slows to a crawl (<4K rows/s in profiling) and memory grows
# unbounded.
#
# We replace it with a counter that produces "user{n}@example.com" values.
# These are unique by construction, O(1), and need no memoization. The
# domain is fake, the local part encodes an ordinal — same end-use semantics
# (a fake, unique email), ~25× faster, constant memory.
#
# The counter uses a list cell rather than a plain int so the lambdas below
# can mutate it (Python 2-style nonlocal workaround that also works in 3).
_email_counter = [0]

def _unique_email():
    _email_counter[0] += 1
    return f"user{_email_counter[0]}@example.com"


# ── Shared-identifier realism ────────────────────────────────────────────────
# Real datasets have natural overlap on identifier-like properties: family
# members share phone numbers, businesses share IPs, address typos produce
# accidental duplicates, fraudsters reuse identifiers. The default generator
# produces zero collisions because each Faker call is independent — that
# makes any "find shared identifier" query return zero results, which is the
# wrong baseline for similarity / fraud / entity-resolution work.
#
# When --shared-identifiers is set, for each configured property name we
# pre-generate a "shared pool" (smaller than the population). When a row
# is generated, with probability p, we take a value from the shared pool
# (collisions happen); otherwise we generate a fresh value as normal.
#
# The pool size is set so that average cluster size ≈ user-specified size:
# if x% of N rows pull from a pool of size K, expected cluster size ≈
# (x*N) / K, so K = (x*N) / cluster_size.
#
# Configuration shape (from argparse):
#   {"phone": {"share_pct": 0.10, "cluster_min": 3, "cluster_max": 5},
#    "email": {"share_pct": 0.02, "cluster_min": 2, "cluster_max": 3}, ...}
SHARED_IDENTIFIER_CONFIG = {}
SHARED_IDENTIFIER_POOLS = {}    # property_name → list of pre-generated values


def _init_shared_identifier_pools(config, node_counts_by_label, schema_nodes):
    """
    For each configured shared-identifier property, pre-generate a pool whose
    size is calibrated to produce the requested average cluster size.

    config: parsed --shared-identifiers config
    node_counts_by_label: {"Customer": 200000, ...}
    schema_nodes: the schema's node defs (so we can find which labels have
                  this property, to size the pool against actual population)
    """
    for prop_name, params in config.items():
        # Find the population: how many rows total will have this property?
        # (Sum across all node types where the property appears.)
        population = 0
        for node_def in schema_nodes:
            if prop_name in node_def.get("properties", {}):
                label = node_def["labels"][0] if node_def.get("labels") else node_def.get("caption", "Node")
                population += node_counts_by_label.get(label, 0)

        if population == 0:
            print(f"WARN: --shared-identifiers references '{prop_name}' but no "
                  f"node has that property; skipping", file=sys.stderr)
            continue

        share_pct = params["share_pct"]
        cluster_size = (params["cluster_min"] + params["cluster_max"]) / 2

        # K = (share_pct * N) / cluster_size, floored to at least 1
        pool_size = max(1, int((share_pct * population) / cluster_size))

        # Generate the pool by calling the appropriate generator. We need a
        # baseline generator for this property; use get_generator() with no
        # label context (label-aware generators may produce different values
        # per label, but the shared pool is global — fine for identifiers).
        gen = get_generator(prop_name, "string")

        # Disable shared-identifier interception while building the pool
        # (avoid recursion: pool values shouldn't themselves be drawn from
        # an under-construction pool).
        prev_pool = SHARED_IDENTIFIER_POOLS.get(prop_name)
        SHARED_IDENTIFIER_POOLS[prop_name] = None
        try:
            pool = []
            for _ in range(pool_size):
                try:
                    pool.append(gen())
                except Exception:
                    pool.append(f"shared_{prop_name}_{len(pool)}")
            SHARED_IDENTIFIER_POOLS[prop_name] = pool
        finally:
            if prev_pool is not None and SHARED_IDENTIFIER_POOLS.get(prop_name) is None:
                SHARED_IDENTIFIER_POOLS[prop_name] = prev_pool

        print(f"   Shared pool for '{prop_name}': {pool_size} values, "
              f"target {share_pct*100:.0f}% of {population:,} rows in clusters "
              f"of ~{cluster_size:.1f}", file=sys.stderr)


def _maybe_shared_value(prop_name, fresh_generator):
    """
    Either return a value from the shared pool (with configured probability)
    or call fresh_generator() for a unique value. Falls through to fresh
    generation if the property isn't configured for sharing.
    """
    config = SHARED_IDENTIFIER_CONFIG.get(prop_name)
    pool = SHARED_IDENTIFIER_POOLS.get(prop_name)
    if config and pool:
        if random.random() < config["share_pct"]:
            return pool[random.randrange(len(pool))]
    return fresh_generator()


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
    "email": _unique_email,
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
    "email": _unique_email,
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

# ═══════════════════════════════════════════════════════════════════════════════
# Node count computation (unchanged from original — works at any scale)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_node_counts(schema, base_scale):
    """
    Compute how many nodes to generate per label based on relationship topology.
    The most-connected node type gets base_scale; others scale down proportionally.
    """
    nodes = schema.get("nodes", [])
    relationships = schema.get("relationships", [])
    if not nodes:
        return {}

    rel_count = {}
    for n in nodes:
        rel_count[n["id"]] = 0
    for r in relationships:
        rel_count.setdefault(r["fromId"], 0)
        rel_count.setdefault(r["toId"], 0)
        rel_count[r["fromId"]] += 1
        rel_count[r["toId"]] += 1

    max_rels = max(rel_count.values()) if rel_count else 1
    counts = {}
    for n in nodes:
        nid = n["id"]
        label = n["labels"][0] if n.get("labels") else n.get("caption", nid)
        connectivity = rel_count.get(nid, 0)
        ratio = max(0.2, connectivity / max_rels) if max_rels > 0 else 1.0
        counts[nid] = {"label": label, "count": max(10, int(base_scale * ratio))}
    return counts


# ═══════════════════════════════════════════════════════════════════════════════
# ID index: abstraction over how we store node _id values per node type.
#
# At scale < STREAMING_THRESHOLD we keep them in a Python list (simple, fast).
# At scale ≥ STREAMING_THRESHOLD we append them to a packed binary file on disk
# (16 bytes per UUID). We only need two operations for relationship generation:
#   - len(index)            → know how big the source/target pool is
#   - index.sample(k)        → pick k ids, possibly with a distribution
# This avoids holding tens of millions of UUID strings in RAM.
# ═══════════════════════════════════════════════════════════════════════════════

class InMemoryIdIndex:
    """Holds node _id values in a Python list. Used for scale < STREAMING_THRESHOLD."""

    def __init__(self, label):
        self.label = label
        self.ids = []

    def append(self, uuid_str):
        self.ids.append(uuid_str)

    def close(self):
        pass

    def __len__(self):
        return len(self.ids)

    def get(self, i):
        return self.ids[i]

    def sample_indices(self, k, distribution="powerlaw", rng=None):
        rng = rng or random
        n = len(self.ids)
        if n == 0:
            return []
        if distribution == "uniform":
            return [rng.randrange(n) for _ in range(k)]
        # power-law: a small number of "hub" indices get picked disproportionately
        return _powerlaw_sample_indices(n, k, rng)

    def resolve(self, idx):
        return self.ids[idx]


class DiskIdIndex:
    """
    Packs UUID _id values into a fixed-width binary file (16 bytes each).
    Used for scale ≥ STREAMING_THRESHOLD to keep memory flat.

    Write phase: buffered binary writes (append-only).
    Read phase:  memory-mapped random access. OS page cache handles hot pages
                 efficiently — each resolve() is a slice into an mmap object,
                 ~50-100x faster than seek()+read() per lookup.
    """
    RECORD_SIZE = 16                    # UUID is 16 bytes packed
    WRITE_BUF = 64 * 1024               # flush to disk in 64KB chunks

    def __init__(self, label, path):
        import io
        self.label = label
        self.path = path
        # buffered writer → significantly fewer syscalls during generation
        self._write_fp = io.BufferedWriter(io.FileIO(path, "wb"), buffer_size=self.WRITE_BUF)
        self._count = 0
        self._mmap = None
        self._mmap_fp = None

    def append(self, uuid_str):
        # uuid_str is a canonical UUID like "550e8400-e29b-41d4-a716-446655440000"
        hex_only = uuid_str.replace("-", "")
        self._write_fp.write(bytes.fromhex(hex_only))
        self._count += 1

    def close(self):
        """Transition from write-phase to read-phase. Must be called before resolve()."""
        import mmap
        if self._write_fp:
            self._write_fp.flush()
            self._write_fp.close()
            self._write_fp = None
        if self._count == 0:
            return  # nothing to mmap
        self._mmap_fp = open(self.path, "rb")
        self._mmap = mmap.mmap(
            self._mmap_fp.fileno(), 0, access=mmap.ACCESS_READ
        )

    def __len__(self):
        return self._count

    def resolve(self, idx):
        """Return the UUID at position idx as a canonical string."""
        offset = idx * self.RECORD_SIZE
        b = self._mmap[offset:offset + self.RECORD_SIZE]
        h = b.hex()
        return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

    def sample_indices(self, k, distribution="powerlaw", rng=None):
        rng = rng or random
        n = self._count
        if n == 0:
            return []
        if distribution == "uniform":
            return [rng.randrange(n) for _ in range(k)]
        return _powerlaw_sample_indices(n, k, rng)


def _powerlaw_sample_indices(n, k, rng):
    """
    Sample k indices from [0, n) with a power-law bias toward low indices.
    We use the inverse-CDF of a bounded Pareto-like distribution:
        idx = floor(n * (1 - u^(1/alpha)))
    with alpha=1.5 (mild skew — a few hubs, many leaves, tail that isn't extreme).
    This keeps the full range reachable, so leaf nodes still get some edges.
    """
    alpha = 1.5
    out = [0] * k
    for i in range(k):
        u = rng.random()
        # avoid u=0 edge case producing idx=n
        idx = int(n * (1.0 - u ** (1.0 / alpha)))
        if idx >= n:
            idx = n - 1
        out[i] = idx
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Chunked CSV writer: one logical "CSV" for a label/rel type that may span
# multiple physical .csv files when the row count exceeds CHUNK_SIZE.
# ═══════════════════════════════════════════════════════════════════════════════

class ChunkedCsvWriter:
    """
    Writes rows to one or more CSV files. Splits into part1.csv, part2.csv, ...
    when total_expected_rows >= CHUNK_THRESHOLD. Otherwise writes a single file.
    """

    def __init__(self, output_dir, basename, fieldnames, total_expected_rows):
        self.output_dir = output_dir
        self.basename = basename               # e.g. "nodes_person"
        self.fieldnames = fieldnames
        self.chunked = total_expected_rows >= CHUNK_THRESHOLD
        self.total_expected = total_expected_rows
        self.files_written = []
        self._part_num = 0
        self._current_fp = None
        self._current_writer = None
        self._current_count = 0
        self._total_written = 0
        self._open_next_part()

    def _current_filename(self):
        if self.chunked:
            return f"{self.basename}_part{self._part_num}.csv"
        return f"{self.basename}.csv"

    def _open_next_part(self):
        if self._current_fp:
            self._current_fp.close()
        self._part_num += 1
        filename = self._current_filename()
        filepath = os.path.join(self.output_dir, filename)
        self._current_fp = open(filepath, "w", newline="", encoding="utf-8")
        self._current_writer = csv.DictWriter(self._current_fp, fieldnames=self.fieldnames)
        self._current_writer.writeheader()
        self._current_count = 0
        self.files_written.append(filename)

    def write(self, row):
        if self.chunked and self._current_count >= CHUNK_SIZE:
            self._open_next_part()
        self._current_writer.writerow(row)
        self._current_count += 1
        self._total_written += 1

    def close(self):
        if self._current_fp:
            self._current_fp.close()
            self._current_fp = None

    def total(self):
        return self._total_written


# ═══════════════════════════════════════════════════════════════════════════════
# Progress reporter
# ═══════════════════════════════════════════════════════════════════════════════

class Progress:
    def __init__(self, label, total, enabled=True):
        self.label = label
        self.total = total
        self.enabled = enabled
        self.start = time.time()
        self.last_print = self.start
        self.done = 0

    def tick(self, n=1):
        self.done += n
        if not self.enabled:
            return
        if self.done % PROGRESS_EVERY == 0 or self.done == self.total:
            now = time.time()
            # at least 2s between prints to avoid spam
            if now - self.last_print >= 2.0 or self.done == self.total:
                pct = (self.done / self.total * 100.0) if self.total else 100.0
                rate = self.done / max(1e-6, now - self.start)
                print(f"   … {self.label}: {self.done:,} / {self.total:,} "
                      f"({pct:.0f}%, {rate:,.0f} rows/s)",
                      file=sys.stderr, flush=True)
                self.last_print = now


# ═══════════════════════════════════════════════════════════════════════════════
# Node generation (streaming-aware)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_nodes_streaming(node_def, count, output_dir, id_index, show_progress):
    """
    Generate `count` node rows for one node type, writing to CSV (chunked if big)
    and appending each _id to the id_index as we go. Never holds all rows in memory.
    """
    props = node_def.get("properties", {})
    label = node_def["labels"][0] if node_def.get("labels") else node_def.get("caption", "Node")

    # Build column list: _id first, then schema properties
    fieldnames = ["_id"] + list(props.keys())

    # Bind generators once (outside loop) for speed
    generators = [(p, get_generator(p, t, label)) for p, t in props.items()]

    # Preserve label case so downstream ingestion can use the filename as the
    # label directly (Neo4j labels are case-sensitive). Only replace whitespace.
    basename = f"nodes_{label.replace(' ', '_')}"
    writer = ChunkedCsvWriter(output_dir, basename, fieldnames, count)
    progress = Progress(f"{label} nodes", count, enabled=show_progress)

    for i in range(count):
        uuid_str = fake.uuid4()
        row = {"_id": uuid_str}
        for col, gen in generators:
            try:
                row[col] = _maybe_shared_value(col, gen)
            except Exception:
                row[col] = f"{col}_{i}"
        writer.write(row)
        id_index.append(uuid_str)
        progress.tick()

    writer.close()
    id_index.close()
    return writer.files_written, writer.total()


# ═══════════════════════════════════════════════════════════════════════════════
# Relationship generation (streaming-aware, distribution-aware)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_rel_count(from_size, to_size, scale, is_self_loop, cardinality="N:N",
                      nn_fanout=2):
    """
    How many relationships to generate for one schema-relationship.

    Cardinality semantics (driven by --cardinality CLI flag, default N:N):
      1:1 → exactly min(from_size, to_size). Each from has one to, each to one from.
      1:N → exactly to_size edges. Each "to" belongs to one "from"; each "from"
            connects to many. (E.g. Customer-OWNS-Account: each Account has one
            Customer; one Customer can own multiple Accounts.)
      N:1 → exactly from_size edges. Mirror of 1:N.
      N:N → max(from_size, to_size) * nn_fanout. Each side connects to ~fanout
            on the other. Self-loops get halved (self-rels get dense fast).

    nn_fanout defaults to 2 — interpretable as "each entity has on average
    `nn_fanout` relationships of this type." Past versions used 3, which
    over-generated for most schemas; 2 is closer to realistic graphs.

    The hard cap (3× scale) is kept as a safety rail for misconfigured N:N
    relationships at XL scale.
    """
    if cardinality == "1:1":
        return max(10, min(from_size, to_size))
    if cardinality == "1:N":
        return max(10, to_size)
    if cardinality == "N:1":
        return max(10, from_size)
    # N:N (default)
    base = int(max(from_size, to_size) * nn_fanout)
    if is_self_loop:
        base = base // 2
    return max(10, min(base, scale * 3))


def resolve_rel_count(rel_type, from_size, to_size, scale, is_self_loop,
                      cardinality, default_nn_fanout,
                      rel_fanout_map, rel_counts_cap):
    """
    Resolve the final relationship count for one rel-type, applying overrides
    in this order:
      1. Per-rel fanout override (--rel-fanout REL=multiplier) — used for N:N
         only; ignored for 1:1/1:N/N:1 since those are exact counts.
      2. Base count from compute_rel_count() with the resolved fanout.
      3. Absolute cap (--rel-counts REL=count) — final ceiling.
    """
    effective_fanout = rel_fanout_map.get(rel_type, default_nn_fanout)
    base = compute_rel_count(from_size, to_size, scale, is_self_loop,
                             cardinality=cardinality, nn_fanout=effective_fanout)
    if rel_type in rel_counts_cap:
        base = min(base, rel_counts_cap[rel_type])
    return max(10, base)


def _generate_exact_one_to_many(rel_def, from_index, to_index, output_dir,
                                num_rels, props, distribution, show_progress,
                                rng, many_side):
    """
    1:N or N:1 generation: each node on the "many" side gets exactly one
    edge. Iterate the many-side in order, pick a random partner from the
    other side. Guarantees the cardinality contract (no orphans, no
    duplicates on the singleton side... wait, that's not true — multiple
    many-side nodes can share the same singleton, which is the whole
    point of 1:N).

    many_side="to": for 1:N. Each "to" node gets one "from" partner.
                    Result: exactly to_size edges.
    many_side="from": for N:1. Each "from" node gets one "to" partner.
                      Result: exactly from_size edges.
    """
    rel_type = rel_def.get("type", "RELATED_TO")

    fieldnames = ["_from_id", "_to_id"] + list(props.keys())
    prop_generators = [(p, get_generator(p, t)) for p, t in props.items()]

    basename = f"rels_{rel_type}"
    writer = ChunkedCsvWriter(output_dir, basename, fieldnames, num_rels)
    progress = Progress(f"{rel_type} rels", num_rels, enabled=show_progress)

    if many_side == "to":
        many_size = len(to_index)
        one_size = len(from_index)
        many_index, one_index = to_index, from_index
    else:
        many_size = len(from_index)
        one_size = len(to_index)
        many_index, one_index = from_index, to_index

    # If the caller passed a num_rels smaller than many_size (e.g. via
    # --rel-counts cap), respect it: only generate edges for the first
    # num_rels many-side nodes. Otherwise iterate all of many_size.
    iter_limit = min(num_rels, many_size)

    BATCH = 10_000
    written = 0

    # Iterate every position on the many side; pick a partner for each.
    # Power-law on the singleton-side picks: a few "from" nodes (or "to")
    # accumulate disproportionately many partners, which is realistic
    # (e.g. a few super-customers own most accounts).
    for batch_start in range(0, iter_limit, BATCH):
        batch_end = min(batch_start + BATCH, iter_limit)
        batch_k = batch_end - batch_start
        partners = one_index.sample_indices(batch_k, distribution, rng)

        for offset, partner_idx in enumerate(partners):
            many_idx = batch_start + offset
            if many_side == "to":
                from_id = one_index.resolve(partner_idx)
                to_id = many_index.resolve(many_idx)
            else:
                from_id = many_index.resolve(many_idx)
                to_id = one_index.resolve(partner_idx)

            row = {"_from_id": from_id, "_to_id": to_id}
            for col, gen in prop_generators:
                try:
                    row[col] = gen()
                except Exception:
                    row[col] = f"{col}_{written}"
            writer.write(row)
            written += 1
            progress.tick()

    writer.close()
    return writer.files_written, written


def _generate_exact_one_to_one(rel_def, from_index, to_index, output_dir,
                               num_rels, props, distribution, show_progress, rng):
    """
    1:1 generation: pair `from` and `to` so each appears exactly once.
    Uses min(from_size, to_size) edges; truncates the larger side.
    Pairings are by position with a shuffled offset to avoid trivially
    aligned pairs (which would couple the random orders of the two sides).
    """
    rel_type = rel_def.get("type", "RELATED_TO")

    fieldnames = ["_from_id", "_to_id"] + list(props.keys())
    prop_generators = [(p, get_generator(p, t)) for p, t in props.items()]

    basename = f"rels_{rel_type}"
    writer = ChunkedCsvWriter(output_dir, basename, fieldnames, num_rels)
    progress = Progress(f"{rel_type} rels", num_rels, enabled=show_progress)

    n = min(len(from_index), len(to_index))

    # Shift the "to" index by a random offset so pairings aren't trivially
    # identity-aligned. Both sides have UUIDs anyway so this is mostly
    # belt-and-braces.
    offset = rng.randrange(1, max(2, n))
    written = 0
    for i in range(n):
        from_id = from_index.resolve(i)
        to_id = to_index.resolve((i + offset) % len(to_index))
        row = {"_from_id": from_id, "_to_id": to_id}
        for col, gen in prop_generators:
            try:
                row[col] = gen()
            except Exception:
                row[col] = f"{col}_{written}"
        writer.write(row)
        written += 1
        progress.tick()

    writer.close()
    return writer.files_written, written


def generate_rels_streaming(rel_def, from_index, to_index, output_dir,
                            scale, distribution, show_progress, rng,
                            cardinality="N:N", nn_fanout=2, num_rels=None):
    """
    Generate relationships for one relationship type using the two id indexes.
    Writes directly to CSV (chunked if big). Never materialises the edge list
    in memory.

    If num_rels is provided, use it directly (caller has already applied any
    per-rel overrides). Otherwise compute it from compute_rel_count().
    """
    props = rel_def.get("properties", {})
    rel_type = rel_def.get("type", "RELATED_TO")
    is_self = rel_def["fromId"] == rel_def["toId"]

    from_size = len(from_index)
    to_size = len(to_index)
    if from_size == 0 or to_size == 0:
        return [], 0

    if num_rels is None:
        num_rels = compute_rel_count(from_size, to_size, scale, is_self,
                                     cardinality=cardinality, nn_fanout=nn_fanout)

    # 1:N and N:1 generate "exact" counts where each minority-side node
    # gets exactly one edge. Use targeted iteration for these instead of
    # random sampling — guarantees the cardinality contract.
    if cardinality == "1:N":
        return _generate_exact_one_to_many(
            rel_def, from_index, to_index, output_dir,
            num_rels, props, distribution, show_progress, rng,
            many_side="to"
        )
    if cardinality == "N:1":
        return _generate_exact_one_to_many(
            rel_def, from_index, to_index, output_dir,
            num_rels, props, distribution, show_progress, rng,
            many_side="from"
        )
    if cardinality == "1:1":
        return _generate_exact_one_to_one(
            rel_def, from_index, to_index, output_dir,
            num_rels, props, distribution, show_progress, rng
        )

    # N:N: random sampling (existing logic)

    fieldnames = ["_from_id", "_to_id"] + list(props.keys())
    prop_generators = [(p, get_generator(p, t)) for p, t in props.items()]

    # Preserve rel-type case — Neo4j convention is UPPER_SNAKE_CASE, lowercasing
    # would force ingestion to re-look-up the canonical form.
    basename = f"rels_{rel_type}"
    writer = ChunkedCsvWriter(output_dir, basename, fieldnames, num_rels)
    progress = Progress(f"{rel_type} rels", num_rels, enabled=show_progress)

    # Sample indices in batches to amortise overhead and keep memory flat
    BATCH = 10_000
    written = 0
    # We track recent (from,to) pairs in a bounded set to avoid immediate
    # duplicates without blowing memory for high-scale runs.
    recent_pairs = set()
    RECENT_CAP = 50_000

    while written < num_rels:
        batch_k = min(BATCH, num_rels - written)
        from_idx = from_index.sample_indices(batch_k, distribution, rng)
        to_idx = to_index.sample_indices(batch_k, distribution, rng)

        for fi, ti in zip(from_idx, to_idx):
            if is_self and fi == ti:
                # Avoid trivial self-edges; nudge target
                ti = (ti + 1) % to_size
            pair_key = (fi, ti)
            if pair_key in recent_pairs:
                continue
            recent_pairs.add(pair_key)
            if len(recent_pairs) > RECENT_CAP:
                # simple bounded-set strategy: clear and continue
                recent_pairs.clear()

            row = {
                "_from_id": from_index.resolve(fi),
                "_to_id": to_index.resolve(ti),
            }
            for col, gen in prop_generators:
                try:
                    row[col] = gen()
                except Exception:
                    row[col] = f"{col}_{written}"
            writer.write(row)
            written += 1
            progress.tick()
            if written >= num_rels:
                break

    writer.close()
    return writer.files_written, written


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Generate fake graph data from a schema")
    parser.add_argument("schema", help="Path to arrows.app JSON schema file")
    parser.add_argument("--output-dir", "-o", default="./graph_data",
                        help="Output directory for CSV files")
    parser.add_argument("--scale", "-s", type=int, default=1000,
                        help="Anchor count for the largest node type")
    parser.add_argument("--flavor", choices=["generic", "healthcare", "finance",
                                             "ecommerce", "social"],
                        default="generic",
                        help="Domain flavor (sets default locale; (label,prop) context "
                             "generators already dispatch on label names regardless)")
    parser.add_argument("--locale", default=None,
                        help="Faker locale (e.g. en_US, en_GB, de_DE). "
                             "Overrides flavor default.")
    parser.add_argument("--distribution", choices=["powerlaw", "uniform"],
                        default="powerlaw",
                        help="Relationship fanout distribution. 'powerlaw' (default) "
                             "mimics real graphs; 'uniform' for controlled tests.")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (for reproducibility). Change for fresh data.")
    parser.add_argument("--cardinality", default="",
                        help="Per-relationship cardinality, comma-separated. "
                             "Format: REL_TYPE=1:1|1:N|N:1|N:N. "
                             "Example: 'OWNS=1:N,SHARES_DEVICE=N:N'. "
                             "Unspecified relationships default to N:N.")
    parser.add_argument("--nn-fanout", type=float, default=2.0,
                        help="Multiplier for N:N relationships. Number of edges "
                             "= max(from_size, to_size) * nn_fanout. Default 2.0 "
                             "(each entity averages ~2 partners). Use 1.2 for "
                             "very sparse, 5+ for dense.")
    parser.add_argument("--node-counts", default="",
                        help="Override per-label node counts, comma-separated. "
                             "Format: Label=count,Label2=count2. Bypasses the "
                             "connectivity-based auto-scaling for the listed "
                             "labels; unlisted labels still auto-scale from "
                             "--scale. Example: 'Customer=200000,Transaction=1000000'.")
    parser.add_argument("--rel-fanout", default="",
                        help="Per-relationship N:N fanout overrides, comma-"
                             "separated. Format: REL_TYPE=multiplier. Only "
                             "applies to N:N relationships; ignored for 1:1, "
                             "1:N, N:1 (those are exact counts by definition). "
                             "Example: 'OWNS_TRANSACTION=2.5,USES_DEVICE=1.5'.")
    parser.add_argument("--rel-counts", default="",
                        help="Absolute relationship count caps, comma-separated. "
                             "Format: REL_TYPE=count. Hard ceiling — if the "
                             "computed count would exceed this, cap it. Useful "
                             "when the user wants 'at most 500K of these'. "
                             "Example: 'USES_DEVICE=500000,INVOLVED_IN=500000'.")
    parser.add_argument("--shared-identifiers", default="",
                        help="Inject realistic identifier collisions into "
                             "node properties. Format: prop:pct%:min-max, "
                             "comma-separated. Example: "
                             "'phone:10%:3-5,email:2%:2-3,ip_address:5%:5-15'. "
                             "Reads as: '10%% of phone values are shared in "
                             "clusters of 3 to 5 rows.' Without this flag, "
                             "every value is independently random (zero "
                             "collisions) — fine for ingestion testing, "
                             "wrong baseline for similarity / fraud / entity-"
                             "resolution work.")
    parser.add_argument("--summary", action="store_true",
                        help="Print a summary of generated data")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute and print expected counts as JSON to "
                             "stdout, then exit. Does not generate any data.")
    args = parser.parse_args()

    # Parse --cardinality into a dict: {"OWNS": "1:N", "SHARES_DEVICE": "N:N", ...}
    cardinality_map = {}
    if args.cardinality.strip():
        for entry in args.cardinality.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if "=" not in entry:
                print(f"WARN: ignoring malformed cardinality entry '{entry}' "
                      f"(expected REL_TYPE=1:N)", file=sys.stderr)
                continue
            rel_name, card = entry.split("=", 1)
            card = card.strip().upper()
            if card not in ("1:1", "1:N", "N:1", "N:N"):
                print(f"WARN: invalid cardinality '{card}' for {rel_name}, "
                      f"using N:N", file=sys.stderr)
                card = "N:N"
            cardinality_map[rel_name.strip()] = card

    # Parse --node-counts, --rel-fanout, --rel-counts.
    # All three share the same "key=number,..." shape; helper consolidates parsing.
    def _parse_kv_numeric(spec, value_type, flag_name):
        out = {}
        if not spec.strip():
            return out
        for entry in spec.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if "=" not in entry:
                print(f"WARN: ignoring malformed {flag_name} entry '{entry}' "
                      f"(expected KEY=NUMBER)", file=sys.stderr)
                continue
            key, val = entry.split("=", 1)
            try:
                out[key.strip()] = value_type(val.strip())
            except ValueError:
                print(f"WARN: ignoring {flag_name} entry '{entry}' "
                      f"(value not a number)", file=sys.stderr)
        return out

    node_counts_override = _parse_kv_numeric(args.node_counts, int, "node-counts")
    rel_fanout_map = _parse_kv_numeric(args.rel_fanout, float, "rel-fanout")
    rel_counts_cap = _parse_kv_numeric(args.rel_counts, int, "rel-counts")

    # Parse --shared-identifiers: format is "prop:pct%:min-max,prop2:pct%:min-max"
    # Result: {"phone": {"share_pct": 0.10, "cluster_min": 3, "cluster_max": 5}, ...}
    shared_id_config = {}
    if args.shared_identifiers.strip():
        for entry in args.shared_identifiers.split(","):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split(":")
            if len(parts) != 3:
                print(f"WARN: ignoring malformed --shared-identifiers entry "
                      f"'{entry}' (expected prop:pct%:min-max)", file=sys.stderr)
                continue
            prop_name, pct_str, range_str = parts
            try:
                pct = float(pct_str.rstrip("%").strip()) / 100.0
                if "-" in range_str:
                    cmin, cmax = (int(x) for x in range_str.split("-"))
                else:
                    cmin = cmax = int(range_str)
                if pct <= 0 or pct > 1 or cmin < 1 or cmax < cmin:
                    raise ValueError("range")
            except ValueError:
                print(f"WARN: ignoring --shared-identifiers entry '{entry}' "
                      f"(invalid percentage or cluster range)", file=sys.stderr)
                continue
            shared_id_config[prop_name.strip()] = {
                "share_pct": pct,
                "cluster_min": cmin,
                "cluster_max": cmax,
            }
    # Make config visible to _maybe_shared_value (which is called per-row);
    # the actual pools are built later, after we know node counts.
    global SHARED_IDENTIFIER_CONFIG
    SHARED_IDENTIFIER_CONFIG = shared_id_config

    # ── Set up Faker with chosen locale and seed ────────────────────────────
    locale = args.locale or FLAVOR_DEFAULT_LOCALE.get(args.flavor, "en_US")
    global fake
    fake = Faker(locale)
    Faker.seed(args.seed)
    random.seed(args.seed)
    rng = random.Random(args.seed)  # dedicated RNG for sampling

    # ── Load schema ─────────────────────────────────────────────────────────
    with open(args.schema, "r") as f:
        raw = json.load(f)
    schema = raw.get("graph", raw)
    nodes = schema.get("nodes", [])
    relationships = schema.get("relationships", [])
    if not nodes:
        print("ERROR: No nodes found in schema.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Decide memory strategy
    streaming = args.scale >= STREAMING_THRESHOLD
    chunked = args.scale >= CHUNK_THRESHOLD
    show_progress = streaming  # only print progress for long runs

    # Temp dir for binary ID indexes when streaming
    index_dir = None
    if streaming:
        index_dir = tempfile.mkdtemp(prefix="graph_ids_", dir=args.output_dir)

    # ── Compute per-label counts ────────────────────────────────────────────
    node_counts = compute_node_counts(schema, args.scale)

    # Apply --node-counts overrides. These are keyed by label, but node_counts
    # is keyed by node-id, so translate.
    if node_counts_override:
        unmatched = set(node_counts_override.keys())
        for nid, info in node_counts.items():
            if info["label"] in node_counts_override:
                info["count"] = node_counts_override[info["label"]]
                unmatched.discard(info["label"])
        for label in unmatched:
            print(f"WARN: --node-counts label '{label}' not found in schema, "
                  f"ignored", file=sys.stderr)

    # ── Dry run: emit JSON summary to stdout, then exit ─────────────────────
    if args.dry_run:
        # Rough byte-per-row estimates:
        # - Node row: 36 (uuid) + Σ(~20 per property) + commas + newline ≈ 50 + 20·P
        # - Rel row: 2·36 (uuids) + Σ(~15 per property) + commas + newline ≈ 80 + 15·P
        # These are conservative; actual sizes vary with property values.

        nodes_summary = {}
        nodes_total = 0
        nodes_bytes = 0
        for n in nodes:
            nid = n["id"]
            info = node_counts.get(nid, {"label": "Node", "count": args.scale})
            label = info["label"]
            count = info["count"]
            num_props = len(n.get("properties", {}))
            avg_row_bytes = 50 + 20 * num_props
            nodes_summary[label] = {
                "count": count,
                "properties": num_props,
                "estimated_bytes": count * avg_row_bytes,
            }
            nodes_total += count
            nodes_bytes += count * avg_row_bytes

        rels_summary = {}
        rels_total = 0
        rels_bytes = 0
        for r in relationships:
            rel_type = r.get("type", "RELATED_TO")
            from_nid = r["fromId"]
            to_nid = r["toId"]
            from_size = node_counts.get(from_nid, {}).get("count", 0)
            to_size = node_counts.get(to_nid, {}).get("count", 0)
            from_label = node_counts.get(from_nid, {}).get("label", from_nid)
            to_label = node_counts.get(to_nid, {}).get("label", to_nid)
            cardinality = cardinality_map.get(rel_type, "N:N")
            is_self = from_nid == to_nid
            count = resolve_rel_count(rel_type, from_size, to_size, args.scale,
                                      is_self, cardinality, args.nn_fanout,
                                      rel_fanout_map, rel_counts_cap)
            num_props = len(r.get("properties", {}))
            avg_row_bytes = 80 + 15 * num_props
            rels_summary[rel_type] = {
                "from_label": from_label,
                "to_label": to_label,
                "cardinality": cardinality,
                "count": count,
                "properties": num_props,
                "estimated_bytes": count * avg_row_bytes,
            }
            rels_total += count
            rels_bytes += count * avg_row_bytes

        # Throughput-based runtime estimate. Conservative numbers from
        # measured sandbox runs: ~9K rows/s for names-heavy nodes, ~40K rows/s
        # for relationships. Real perf varies with property complexity.
        est_seconds = (nodes_total / 9_000) + (rels_total / 40_000)

        summary = {
            "scale": args.scale,
            "flavor": args.flavor,
            "locale": locale,
            "nn_fanout": args.nn_fanout,
            "cardinality_overrides": cardinality_map,
            "node_counts_overrides": node_counts_override,
            "rel_fanout_overrides": rel_fanout_map,
            "rel_counts_caps": rel_counts_cap,
            "shared_identifiers": shared_id_config,
            "totals": {
                "nodes": nodes_total,
                "relationships": rels_total,
                "estimated_csv_bytes": nodes_bytes + rels_bytes,
                "estimated_runtime_seconds": int(est_seconds),
            },
            "nodes": nodes_summary,
            "relationships": rels_summary,
        }
        print(json.dumps(summary, indent=2))
        return

    print(f"📊 Generating graph data", file=sys.stderr)
    print(f"   Scale:        {args.scale:,} (anchor count)", file=sys.stderr)
    print(f"   Flavor:       {args.flavor}", file=sys.stderr)
    print(f"   Locale:       {locale}", file=sys.stderr)
    print(f"   Distribution: {args.distribution}", file=sys.stderr)
    print(f"   N:N fanout:   {args.nn_fanout}× (each entity averages "
          f"~{args.nn_fanout:.1f} partners)", file=sys.stderr)
    if cardinality_map:
        card_summary = ", ".join(f"{k}={v}" for k, v in cardinality_map.items())
        print(f"   Cardinality:  {card_summary}", file=sys.stderr)
    else:
        print(f"   Cardinality:  all N:N (no overrides)", file=sys.stderr)
    if node_counts_override:
        nc_summary = ", ".join(f"{k}={v:,}" for k, v in node_counts_override.items())
        print(f"   Node counts:  {nc_summary} (overrides)", file=sys.stderr)
    if rel_fanout_map:
        rf_summary = ", ".join(f"{k}={v}×" for k, v in rel_fanout_map.items())
        print(f"   Rel fanout:   {rf_summary} (per-rel overrides)", file=sys.stderr)
    if rel_counts_cap:
        rc_summary = ", ".join(f"{k}≤{v:,}" for k, v in rel_counts_cap.items())
        print(f"   Rel caps:     {rc_summary}", file=sys.stderr)
    if shared_id_config:
        si_summary = ", ".join(
            f"{k}={int(v['share_pct']*100)}%@{v['cluster_min']}-{v['cluster_max']}"
            for k, v in shared_id_config.items()
        )
        print(f"   Shared ids:   {si_summary}", file=sys.stderr)
    print(f"   Seed:         {args.seed}", file=sys.stderr)
    print(f"   Mode:         {'chunked streaming' if chunked else 'streaming' if streaming else 'in-memory'}",
          file=sys.stderr)
    print(f"   Output:       {os.path.abspath(args.output_dir)}", file=sys.stderr)
    print("", file=sys.stderr)

    # ── Build shared-identifier pools (if any) ──────────────────────────────
    if shared_id_config:
        # Translate node_counts (keyed by node-id) into a label-keyed dict
        # for pool sizing.
        node_counts_by_label = {info["label"]: info["count"]
                                for info in node_counts.values()}
        _init_shared_identifier_pools(shared_id_config, node_counts_by_label, nodes)
        print("", file=sys.stderr)

    # ── Generate nodes ──────────────────────────────────────────────────────
    node_indexes = {}   # node_def_id -> IdIndex
    node_files = {}     # label -> list of CSV filenames
    node_totals = {}    # label -> total row count

    for node_def in nodes:
        nid = node_def["id"]
        info = node_counts.get(nid, {"label": "Node", "count": args.scale})
        label = info["label"]
        count = info["count"]

        if streaming:
            idx_path = os.path.join(index_dir, f"{nid}.ids")
            idx = DiskIdIndex(label, idx_path)
        else:
            idx = InMemoryIdIndex(label)

        files, total = generate_nodes_streaming(
            node_def, count, args.output_dir, idx, show_progress
        )
        node_indexes[nid] = idx
        node_files[label] = files
        node_totals[label] = total
        print(f"   ✅ {label}: {total:,} nodes → {files[0]}"
              + (f" (+{len(files)-1} more parts)" if len(files) > 1 else ""),
              file=sys.stderr)

    print("", file=sys.stderr)

    # ── Generate relationships ──────────────────────────────────────────────
    rel_files = {}       # rel_type -> list of CSV filenames
    rel_totals = {}      # rel_type -> total row count
    rel_endpoints = {}   # rel_type -> (from_label, to_label)

    for rel_def in relationships:
        from_nid = rel_def["fromId"]
        to_nid = rel_def["toId"]
        rel_type = rel_def.get("type", "RELATED_TO")

        from_idx = node_indexes.get(from_nid)
        to_idx = node_indexes.get(to_nid)
        if from_idx is None or to_idx is None or len(from_idx) == 0 or len(to_idx) == 0:
            print(f"   ⚠️  Skipping {rel_type}: missing node data", file=sys.stderr)
            continue

        from_label = node_counts.get(from_nid, {}).get("label", from_nid)
        to_label = node_counts.get(to_nid, {}).get("label", to_nid)

        # Look up cardinality for this rel-type; default N:N if unspecified.
        rel_cardinality = cardinality_map.get(rel_type, "N:N")

        # Resolve target rel count, applying any --rel-fanout / --rel-counts
        # overrides up front so generate_rels_streaming sees the final number.
        target_count = resolve_rel_count(
            rel_type, len(from_idx), len(to_idx), args.scale,
            rel_def["fromId"] == rel_def["toId"], rel_cardinality,
            args.nn_fanout, rel_fanout_map, rel_counts_cap,
        )

        files, total = generate_rels_streaming(
            rel_def, from_idx, to_idx, args.output_dir,
            args.scale, args.distribution, show_progress, rng,
            cardinality=rel_cardinality, nn_fanout=args.nn_fanout,
            num_rels=target_count,
        )
        rel_files[rel_type] = files
        rel_totals[rel_type] = total
        rel_endpoints[rel_type] = (from_label, to_label)
        print(f"   ✅ {from_label} -[{rel_type} {rel_cardinality}]-> {to_label}: "
              f"{total:,} rels → {files[0]}"
              + (f" (+{len(files)-1} more parts)" if len(files) > 1 else ""),
              file=sys.stderr)

    # ── Clean up temp ID index files ────────────────────────────────────────
    if index_dir and os.path.isdir(index_dir):
        try:
            for fn in os.listdir(index_dir):
                os.remove(os.path.join(index_dir, fn))
            os.rmdir(index_dir)
        except OSError:
            pass  # non-fatal; leaves recoverable temp data

    # ── Copy the schema alongside the CSVs ──────────────────────────────────
    # The ingestion skill needs the schema to know which node files connect to
    # which via which relationships (the filesystem alone can't express rel
    # endpoints). We write a copy of the user's original schema rather than
    # inventing a separate manifest format — one source of truth, no drift.
    total_nodes = sum(node_totals.values())
    total_rels = sum(rel_totals.values())

    print(f"\n🎉 Done! {total_nodes:,} nodes, {total_rels:,} relationships",
          file=sys.stderr)

    schema_copy_path = os.path.join(args.output_dir, "schema.json")
    with open(schema_copy_path, "w") as f:
        json.dump(raw, f, indent=2)
    print(f"   Schema:   {schema_copy_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
