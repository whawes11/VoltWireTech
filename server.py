#!/usr/bin/env python3
"""
VoltWire Marketplace - Enterprise Field Service & Subcontracting Platform
Complete Field Nation & WorkMarket model with:
- Monochrome Black & White Theme Architecture
- Separate Dedicated Portals for Clients (Hiring Businesses) vs Contractors (Technicians)
- Dedicated Client Registration (/api/auth/register-client) with Corporate Billing & Net-30 Terms
- Dedicated Contractor Registration (/api/auth/register-contractor) with Legal W-9, Insurance COI & Payout
- Mandatory Insurance Verification Gate for Payment Release
- 10% Standard Marketplace Fee + Pro Membership (2% fee / 0-day instant payout)
- Payout Methods: Standard Bank ACH (Free, 3-day) vs Instant Debit Card (1.5% fee)
- Job Bidding, Client Counter-Offers, and Mutual Agreement Workflow
- On-Site Check-In / Check-Out and Reliability Scoring (On-Time %, Star Rating)
"""

import os
import sys
import json
import sqlite3
import mimetypes
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "marketplace_v2.db")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

PLATFORM_FEE_PCT = 10.0      # 10% standard marketplace fee
PRO_FEE_PCT = 2.0           # 2% fee for Pro 0-day instant payout
INSTANT_DEBIT_FEE_PCT = 1.5 # 1.5% expedited debit card processing fee

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL, -- 'business' or 'contractor'
        company_name TEXT,
        full_name TEXT NOT NULL,
        phone TEXT,
        location TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Clients (Hiring Businesses / MSPs / Facilities) Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        company_name TEXT NOT NULL,
        contact_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        website TEXT,
        industry_type TEXT,
        billing_address TEXT,
        billing_method TEXT DEFAULT 'corporate_card', -- 'corporate_card', 'ach_billing', 'net_30'
        monthly_volume TEXT DEFAULT '5-20 jobs',
        verified INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Contractors Table with Full Compliance & Onboarding Details
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contractors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        contact_person TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        location TEXT NOT NULL,
        specialties TEXT NOT NULL,
        certifications TEXT,
        hourly_rate REAL DEFAULT 75.0,
        rating REAL DEFAULT 5.0,
        on_time_rate REAL DEFAULT 100.0,
        quality_score REAL DEFAULT 98.0,
        completed_jobs INTEGER DEFAULT 0,
        badges TEXT DEFAULT 'Verified Pro, 100% On-Time',
        tax_id_type TEXT DEFAULT 'EIN',
        tax_id_masked TEXT DEFAULT 'XX-XXX4192',
        legal_entity_type TEXT DEFAULT 'LLC',
        id_verified INTEGER DEFAULT 1,
        insurance_carrier TEXT DEFAULT 'Travelers Commercial',
        insurance_policy_number TEXT DEFAULT 'GL-9823441-GA',
        insurance_coverage_amount REAL DEFAULT 1000000.0,
        insurance_expiration TEXT DEFAULT '2027-08-31',
        insurance_verified INTEGER DEFAULT 1,
        payout_method TEXT DEFAULT 'ach',
        bank_name TEXT DEFAULT 'Chase Bank',
        bank_routing_masked TEXT DEFAULT '*****0210',
        bank_account_masked TEXT DEFAULT '******8832',
        debit_card_last4 TEXT DEFAULT '4192',
        is_pro_member INTEGER DEFAULT 0,
        pro_tier TEXT DEFAULT 'Standard',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Jobs Table (Work Orders)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        company_name TEXT NOT NULL,
        location TEXT NOT NULL,
        drop_count INTEGER DEFAULT 0,
        budget_min REAL NOT NULL,
        budget_max REAL NOT NULL,
        agreed_amount REAL DEFAULT 0,
        platform_fee REAL DEFAULT 0,
        contractor_payout REAL DEFAULT 0,
        deadline TEXT,
        description TEXT NOT NULL,
        requirements TEXT,
        status TEXT DEFAULT 'published',
        assigned_contractor_id INTEGER,
        check_in_time TEXT,
        check_out_time TEXT,
        completion_notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES users (id),
        FOREIGN KEY (assigned_contractor_id) REFERENCES contractors (id)
    )
    """)

    # Bids & Negotiation Offers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        contractor_id INTEGER,
        contractor_name TEXT NOT NULL,
        contractor_email TEXT NOT NULL,
        contractor_phone TEXT,
        amount REAL NOT NULL,
        platform_fee REAL DEFAULT 0,
        contractor_payout REAL DEFAULT 0,
        labor_cost REAL DEFAULT 0,
        material_cost REAL DEFAULT 0,
        estimated_days INTEGER DEFAULT 1,
        proposal_notes TEXT NOT NULL,
        counter_offer_amount REAL DEFAULT 0,
        counter_offer_notes TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs (id),
        FOREIGN KEY (contractor_id) REFERENCES contractors (id)
    )
    """)

    # Reviews Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        client_id INTEGER,
        contractor_id INTEGER NOT NULL,
        rating REAL NOT NULL,
        arrived_on_time INTEGER DEFAULT 1,
        review_text TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs (id),
        FOREIGN KEY (contractor_id) REFERENCES contractors (id)
    )
    """)

    # Payouts Settlement Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        contractor_id INTEGER NOT NULL,
        gross_amount REAL NOT NULL,
        platform_fee REAL NOT NULL,
        processing_fee REAL DEFAULT 0,
        net_payout REAL NOT NULL,
        payout_type TEXT NOT NULL,
        processing_days INTEGER DEFAULT 3,
        status TEXT DEFAULT 'processed',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

class MarketplaceHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status=200):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # API Routes
        if path == "/api/jobs":
            self.handle_get_jobs(query)
            return
        elif path.startswith("/api/jobs/") and not "/" in path[10:]:
            job_id = path.split("/")[-1]
            self.handle_get_job_detail(job_id)
            return
        elif path == "/api/contractors":
            self.handle_get_contractors(query)
            return
        elif path == "/api/clients":
            self.handle_get_clients(query)
            return
        elif path.startswith("/api/contractors/"):
            cid = path.split("/")[-1]
            self.handle_get_contractor_profile(cid)
            return
        elif path == "/api/bids":
            self.handle_get_bids(query)
            return
        elif path == "/api/stats":
            self.handle_get_stats()
            return
        elif path == "/api/users":
            self.handle_get_users()
            return
        elif path == "/api/my-jobs":
            self.handle_get_my_jobs(query)
            return
        elif path == "/api/payouts":
            self.handle_get_payouts(query)
            return

        # Static / Web Assets
        if path == "/" or path == "":
            file_path = os.path.join(STATIC_DIR, "index.html")
        else:
            rel_path = path.lstrip("/")
            file_path = os.path.join(STATIC_DIR, rel_path)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"

            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            self.send_json({"error": "Invalid JSON format"}, 400)
            return

        # Route matching
        if path == "/api/auth/register-client":
            self.handle_register_client(body)
        elif path == "/api/auth/register-contractor":
            self.handle_register_contractor(body)
        elif path == "/api/auth/register":
            self.handle_register_generic(body)
        elif path == "/api/auth/login":
            self.handle_login(body)
        elif path == "/api/jobs":
            self.handle_create_job(body)
        elif path.startswith("/api/jobs/") and path.endswith("/assign"):
            job_id = path.split("/")[3]
            self.handle_assign_job(job_id, body)
        elif path.startswith("/api/jobs/") and path.endswith("/counter"):
            job_id = path.split("/")[3]
            self.handle_counter_offer(job_id, body)
        elif path.startswith("/api/jobs/") and path.endswith("/check-in"):
            job_id = path.split("/")[3]
            self.handle_check_in(job_id, body)
        elif path.startswith("/api/jobs/") and path.endswith("/complete"):
            job_id = path.split("/")[3]
            self.handle_complete_job(job_id, body)
        elif path.startswith("/api/jobs/") and path.endswith("/approve"):
            job_id = path.split("/")[3]
            self.handle_approve_job(job_id, body)
        elif path == "/api/bids":
            self.handle_create_bid(body)
        elif path.startswith("/api/bids/") and path.endswith("/accept-counter"):
            bid_id = path.split("/")[3]
            self.handle_accept_counter(bid_id, body)
        elif path == "/api/contractors/upgrade-pro":
            self.handle_upgrade_pro(body)
        elif path == "/api/contractors/update-compliance":
            self.handle_update_compliance(body)
        elif path == "/api/reviews":
            self.handle_create_review(body)
        else:
            self.send_json({"error": "Endpoint not found"}, 404)

    # --- Dedicated Registration Handlers ---

    def handle_register_client(self, body):
        # Dedicated Onboarding for Hiring Businesses / IT Providers
        required = ["company_name", "contact_name", "email", "password"]
        for r in required:
            if not body.get(r):
                self.send_json({"error": f"Missing required client field: {r}"}, 400)
                return

        email = body["email"].strip().lower()
        username = body.get("username", email.split("@")[0] + "_biz").strip().lower()

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO users (username, email, password, role, company_name, full_name, phone, location)
            VALUES (?, ?, ?, 'business', ?, ?, ?, ?)
            """, (
                username,
                email,
                body["password"],
                body["company_name"],
                body["contact_name"],
                body.get("phone", ""),
                body.get("location", "Atlanta, GA")
            ))
            user_id = cursor.lastrowid

            cursor.execute("""
            INSERT INTO clients (user_id, company_name, contact_name, email, phone, website, industry_type, billing_address, billing_method, monthly_volume, verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                user_id,
                body["company_name"],
                body["contact_name"],
                email,
                body.get("phone", ""),
                body.get("website", ""),
                body.get("industry_type", "Managed Service Provider (MSP)"),
                body.get("billing_address", "Atlanta, GA"),
                body.get("billing_method", "corporate_card"),
                body.get("monthly_volume", "5-20 jobs")
            ))

            conn.commit()
            cursor.execute("SELECT id, username, email, role, company_name, full_name FROM users WHERE id = ?", (user_id,))
            user = dict(cursor.fetchone())
            conn.close()

            self.send_json({
                "success": True,
                "user": user,
                "message": f"Welcome to VoltWire, {body['company_name']}! Your corporate hiring account is active."
            }, 201)
        except sqlite3.IntegrityError:
            conn.close()
            self.send_json({"error": "An account with this email or username already exists."}, 409)

    def handle_register_contractor(self, body):
        # Dedicated Onboarding for Technicians & Installation Crews
        required = ["name", "contact_person", "email", "password"]
        for r in required:
            if not body.get(r):
                self.send_json({"error": f"Missing required contractor field: {r}"}, 400)
                return

        email = body["email"].strip().lower()
        username = body.get("username", email.split("@")[0] + "_tech").strip().lower()

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO users (username, email, password, role, company_name, full_name, phone, location)
            VALUES (?, ?, ?, 'contractor', ?, ?, ?, ?)
            """, (
                username,
                email,
                body["password"],
                body["name"],
                body["contact_person"],
                body.get("phone", ""),
                body.get("location", "Atlanta, GA")
            ))
            user_id = cursor.lastrowid

            cov_amt = float(body.get("insurance_coverage_amount", 1000000.0))
            ins_verified = 1 if cov_amt >= 1000000.0 else 0
            is_pro = 1 if body.get("pro_membership") else 0

            cursor.execute("""
            INSERT INTO contractors (
                user_id, name, contact_person, email, phone, location, specialties, certifications,
                hourly_rate, tax_id_type, tax_id_masked, legal_entity_type, id_verified,
                insurance_carrier, insurance_policy_number, insurance_coverage_amount,
                insurance_expiration, insurance_verified, payout_method, bank_name,
                bank_routing_masked, bank_account_masked, debit_card_last4, is_pro_member, pro_tier
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                body["name"],
                body["contact_person"],
                email,
                body.get("phone", ""),
                body.get("location", "Atlanta, GA"),
                body.get("specialties", "Structured Cabling, CCTV & IP Cameras, Network Devices"),
                body.get("certifications", body.get("license", "Verified Technician")),
                float(body.get("hourly_rate", 75.0)),
                body.get("tax_id_type", "EIN"),
                "XX-XXX" + str(body.get("tax_id", "4192"))[-4:],
                body.get("legal_entity_type", "LLC"),
                1,
                body.get("insurance_carrier", "Travelers Commercial"),
                body.get("insurance_policy_number", f"GL-{user_id}881-GA"),
                cov_amt,
                body.get("insurance_expiration", "2027-12-31"),
                ins_verified,
                body.get("payout_method", "ach"),
                body.get("bank_name", "Chase Bank"),
                "*****" + str(body.get("bank_routing", "0210"))[-4:],
                "******" + str(body.get("bank_account", "8832"))[-4:],
                str(body.get("debit_card", "4192"))[-4:],
                is_pro,
                "Pro Member (0-Day Payout)" if is_pro else "Standard"
            ))

            conn.commit()
            cursor.execute("SELECT id, username, email, role, company_name, full_name FROM users WHERE id = ?", (user_id,))
            user = dict(cursor.fetchone())
            conn.close()

            self.send_json({
                "success": True,
                "user": user,
                "message": f"Welcome to VoltWire, {body['contact_person']}! Your contractor profile and compliance documentation are approved."
            }, 201)
        except sqlite3.IntegrityError:
            conn.close()
            self.send_json({"error": "An account with this email or username already exists."}, 409)

    def handle_register_generic(self, body):
        if body.get("role") == "business":
            self.handle_register_client({
                "company_name": body.get("company_name", body.get("full_name")),
                "contact_name": body.get("full_name"),
                "email": body.get("email"),
                "password": body.get("password"),
                "phone": body.get("phone", ""),
                "username": body.get("username")
            })
        else:
            self.handle_register_contractor({
                "name": body.get("company_name", body.get("full_name")),
                "contact_person": body.get("full_name"),
                "email": body.get("email"),
                "password": body.get("password"),
                "phone": body.get("phone", ""),
                "username": body.get("username")
            })

    def handle_login(self, body):
        username = body.get("username", "").strip().lower()
        password = body.get("password", "")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE (username = ? OR email = ?) AND password = ?", (username, username, password))
        row = cursor.fetchone()
        if not row:
            conn.close()
            self.send_json({"error": "Invalid email/username or password."}, 401)
            return

        user = dict(row)
        del user["password"]

        if user["role"] == "contractor":
            cursor.execute("SELECT id, insurance_verified, is_pro_member FROM contractors WHERE user_id = ?", (user["id"],))
            c_row = cursor.fetchone()
            if c_row:
                user["contractor_id"] = c_row["id"]
                user["insurance_verified"] = c_row["insurance_verified"]
                user["is_pro_member"] = c_row["is_pro_member"]
        else:
            cursor.execute("SELECT id, billing_method, monthly_volume FROM clients WHERE user_id = ?", (user["id"],))
            cl_row = cursor.fetchone()
            if cl_row:
                user["client_id"] = cl_row["id"]
                user["billing_method"] = cl_row["billing_method"]

        conn.close()
        self.send_json({"success": True, "user": user})

    def handle_get_users(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, company_name, full_name, location FROM users")
        users = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.send_json({"users": users})

    def handle_get_clients(self, query):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients ORDER BY created_at DESC")
        clients = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.send_json({"clients": clients, "count": len(clients)})

    # --- Work Orders & Negotiation ---

    def handle_get_jobs(self, query):
        conn = get_db()
        cursor = conn.cursor()

        sql = "SELECT j.*, (SELECT COUNT(*) FROM bids WHERE job_id = j.id) AS bid_count FROM jobs j WHERE 1=1"
        params = []

        if "category" in query and query["category"][0]:
            sql += " AND j.category = ?"
            params.append(query["category"][0])

        if "status" in query and query["status"][0]:
            sql += " AND j.status = ?"
            params.append(query["status"][0])

        if "search" in query and query["search"][0]:
            search_term = f"%{query['search'][0]}%"
            sql += " AND (j.title LIKE ? OR j.description LIKE ? OR j.location LIKE ? OR j.company_name LIKE ?)"
            params.extend([search_term, search_term, search_term, search_term])

        sql += " ORDER BY j.created_at DESC"
        cursor.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()

        self.send_json({"jobs": rows, "count": len(rows)})

    def handle_get_job_detail(self, job_id):
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT j.*, c.name as assigned_contractor_name, c.insurance_verified, c.is_pro_member
        FROM jobs j
        LEFT JOIN contractors c ON j.assigned_contractor_id = c.id
        WHERE j.id = ?
        """, (job_id,))
        job = cursor.fetchone()
        if not job:
            conn.close()
            self.send_json({"error": "Work order not found"}, 404)
            return

        job_dict = dict(job)
        cursor.execute("SELECT * FROM bids WHERE job_id = ? ORDER BY amount ASC", (job_id,))
        bids = [dict(row) for row in cursor.fetchall()]
        job_dict["bids"] = bids

        cursor.execute("SELECT * FROM reviews WHERE job_id = ?", (job_id,))
        reviews = [dict(row) for row in cursor.fetchall()]
        job_dict["reviews"] = reviews

        cursor.execute("SELECT * FROM payouts WHERE job_id = ?", (job_id,))
        payouts = [dict(row) for row in cursor.fetchall()]
        job_dict["payouts"] = payouts

        conn.close()
        self.send_json({"job": job_dict})

    def handle_create_job(self, body):
        required = ["title", "category", "company_name", "location", "budget_min", "budget_max", "description"]
        for field in required:
            if not body.get(field):
                self.send_json({"error": f"Missing required field: {field}"}, 400)
                return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO jobs (client_id, title, category, company_name, location, drop_count, budget_min, budget_max, deadline, description, requirements, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            body.get("client_id", 1),
            body["title"],
            body["category"],
            body["company_name"],
            body["location"],
            int(body.get("drop_count", 0)),
            float(body["budget_min"]),
            float(body["budget_max"]),
            body.get("deadline", ""),
            body["description"],
            body.get("requirements", "General Liability Insurance ($1M+) required"),
            "published"
        ))
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.send_json({"success": True, "job_id": job_id, "message": "Work Order published to marketplace"}, 201)

    def handle_counter_offer(self, job_id, body):
        bid_id = body.get("bid_id")
        counter_amount = float(body.get("counter_amount", 0))
        counter_notes = body.get("counter_notes", "Client proposed adjusted budget.")

        if not bid_id or counter_amount <= 0:
            self.send_json({"error": "bid_id and counter_amount required"}, 400)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE bids
        SET counter_offer_amount = ?, counter_offer_notes = ?, status = 'countered'
        WHERE id = ? AND job_id = ?
        """, (counter_amount, counter_notes, bid_id, job_id))

        cursor.execute("UPDATE jobs SET status = 'negotiating' WHERE id = ?", (job_id,))
        conn.commit()
        conn.close()

        self.send_json({"success": True, "message": f"Counter offer of ${counter_amount:.2f} sent to contractor."})

    def handle_accept_counter(self, bid_id, body):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bids WHERE id = ?", (bid_id,))
        bid = cursor.fetchone()
        if not bid:
            conn.close()
            self.send_json({"error": "Bid not found"}, 404)
            return

        agreed = bid["counter_offer_amount"]
        fee = round(agreed * (PLATFORM_FEE_PCT / 100.0), 2)
        payout = round(agreed - fee, 2)

        cursor.execute("UPDATE bids SET amount = ?, status = 'accepted' WHERE id = ?", (agreed, bid_id))
        cursor.execute("""
        UPDATE jobs
        SET status = 'assigned', assigned_contractor_id = ?, agreed_amount = ?, platform_fee = ?, contractor_payout = ?
        WHERE id = ?
        """, (bid["contractor_id"], agreed, fee, payout, bid["job_id"]))

        cursor.execute("UPDATE bids SET status = 'declined' WHERE job_id = ? AND id != ?", (bid["job_id"], bid_id))
        conn.commit()
        conn.close()

        self.send_json({"success": True, "message": f"Agreed to counter-offer: ${agreed:.2f}. Work order assigned."})

    def handle_assign_job(self, job_id, body):
        bid_id = body.get("bid_id")
        if not bid_id:
            self.send_json({"error": "bid_id required"}, 400)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bids WHERE id = ? AND job_id = ?", (bid_id, job_id))
        bid = cursor.fetchone()
        if not bid:
            conn.close()
            self.send_json({"error": "Bid not found"}, 404)
            return

        total_amount = bid["amount"]
        fee = round(total_amount * (PLATFORM_FEE_PCT / 100.0), 2)
        payout = round(total_amount - fee, 2)

        cursor.execute("""
        UPDATE jobs
        SET status = 'assigned', assigned_contractor_id = ?, agreed_amount = ?, platform_fee = ?, contractor_payout = ?
        WHERE id = ?
        """, (bid["contractor_id"], total_amount, fee, payout, job_id))

        cursor.execute("UPDATE bids SET status = 'accepted' WHERE id = ?", (bid_id,))
        cursor.execute("UPDATE bids SET status = 'declined' WHERE job_id = ? AND id != ?", (job_id, bid_id))

        conn.commit()
        conn.close()

        self.send_json({
            "success": True,
            "message": f"Contractor assigned. 10% platform fee (${fee:.2f}) reserved. Net payout: ${payout:.2f}."
        })

    def handle_check_in(self, job_id, body):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE jobs
        SET status = 'in_progress', check_in_time = ?
        WHERE id = ?
        """, (now_str, job_id))
        conn.commit()
        conn.close()

        self.send_json({"success": True, "check_in_time": now_str, "status": "in_progress", "message": "On-Site check-in verified."})

    def handle_complete_job(self, job_id, body):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        notes = body.get("completion_notes", "Work completed according to specifications.")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE jobs
        SET status = 'completed', check_out_time = ?, completion_notes = ?
        WHERE id = ?
        """, (now_str, notes, job_id))
        conn.commit()
        conn.close()

        self.send_json({"success": True, "check_out_time": now_str, "status": "completed", "message": "Deliverables submitted for client approval."})

    def handle_approve_job(self, job_id, body):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT j.*, c.insurance_verified, c.payout_method, c.is_pro_member FROM jobs j JOIN contractors c ON j.assigned_contractor_id = c.id WHERE j.id = ?", (job_id,))
        job = cursor.fetchone()
        if not job:
            conn.close()
            self.send_json({"error": "Job not found"}, 404)
            return

        gross = job["agreed_amount"]
        platform_fee = job["platform_fee"]
        cid = job["assigned_contractor_id"]

        # Check Insurance Compliance Gatekeeper
        if not job["insurance_verified"]:
            cursor.execute("""
            INSERT INTO payouts (job_id, contractor_id, gross_amount, platform_fee, processing_fee, net_payout, payout_type, processing_days, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'held_insurance_required')
            """, (job_id, cid, gross, platform_fee, 0.0, gross - platform_fee, "held", 0))

            cursor.execute("UPDATE jobs SET status = 'approved' WHERE id = ?", (job_id,))
            conn.commit()
            conn.close()

            self.send_json({
                "success": True,
                "status": "approved",
                "insurance_held": True,
                "message": "Job approved, but contractor payout is currently on HOLD because General Liability Insurance certificate ($1M+) is unverified."
            })
            return

        payout_method = job["payout_method"]
        is_pro = job["is_pro_member"]

        if is_pro:
            pro_fee = round(gross * (PRO_FEE_PCT / 100.0), 2)
            net_payout = round(gross - platform_fee - pro_fee, 2)
            payout_type = "pro_zero_day"
            proc_days = 0
            fee_note = f"0-Day Instant Pro Payout (2% Pro fee: ${pro_fee:.2f})"
        elif payout_method == "debit":
            debit_fee = round(gross * (INSTANT_DEBIT_FEE_PCT / 100.0), 2)
            net_payout = round(gross - platform_fee - debit_fee, 2)
            payout_type = "instant_debit"
            proc_days = 0
            fee_note = f"Expedited Debit Card Transfer (1.5% fee: ${debit_fee:.2f})"
        else:
            net_payout = round(gross - platform_fee, 2)
            payout_type = "ach_standard"
            proc_days = 3
            fee_note = "Standard Bank ACH Direct Deposit (3-5 business days, Free)"

        cursor.execute("UPDATE jobs SET status = 'approved' WHERE id = ?", (job_id,))
        cursor.execute("UPDATE contractors SET completed_jobs = completed_jobs + 1 WHERE id = ?", (cid,))

        cursor.execute("""
        INSERT INTO payouts (job_id, contractor_id, gross_amount, platform_fee, processing_fee, net_payout, payout_type, processing_days, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'processed')
        """, (job_id, cid, gross, platform_fee, (gross - platform_fee - net_payout), net_payout, payout_type, proc_days))

        conn.commit()
        conn.close()

        self.send_json({
            "success": True,
            "status": "approved",
            "insurance_held": False,
            "net_payout": net_payout,
            "platform_fee": platform_fee,
            "payout_type": payout_type,
            "processing_days": proc_days,
            "message": f"Job approved! 10% platform fee (${platform_fee:.2f}) collected. Net payout of ${net_payout:.2f} dispatched via {fee_note}."
        })

    def handle_upgrade_pro(self, body):
        contractor_id = body.get("contractor_id")
        if not contractor_id:
            self.send_json({"error": "contractor_id required"}, 400)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE contractors
        SET is_pro_member = 1, pro_tier = 'Pro Member (0-Day Payout)',
            badges = badges || ', Pro Member'
        WHERE id = ?
        """, (contractor_id,))
        conn.commit()
        conn.close()

        self.send_json({"success": True, "message": "Upgraded to Pro Membership. 0-Day instant payouts activated."})

    def handle_update_compliance(self, body):
        contractor_id = body.get("contractor_id")
        if not contractor_id:
            self.send_json({"error": "contractor_id required"}, 400)
            return

        carrier = body.get("insurance_carrier", "Travelers Commercial")
        policy = body.get("insurance_policy_number", "GL-COMM-2026")
        cov_amt = float(body.get("insurance_coverage_amount", 1000000.0))
        payout_method = body.get("payout_method", "ach")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE contractors
        SET insurance_carrier = ?, insurance_policy_number = ?, insurance_coverage_amount = ?,
            insurance_verified = 1, payout_method = ?
        WHERE id = ?
        """, (carrier, policy, cov_amt, payout_method, contractor_id))
        conn.commit()
        conn.close()

        self.send_json({"success": True, "message": "Compliance documentation & insurance policy verified ($1M+). Eligible for payouts."})

    def handle_create_bid(self, body):
        required = ["job_id", "contractor_name", "contractor_email", "amount", "proposal_notes"]
        for field in required:
            if not body.get(field):
                self.send_json({"error": f"Missing required field: {field}"}, 400)
                return

        amount = float(body["amount"])
        fee = round(amount * (PLATFORM_FEE_PCT / 100.0), 2)
        payout = round(amount - fee, 2)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO bids (job_id, contractor_id, contractor_name, contractor_email, contractor_phone, amount, platform_fee, contractor_payout, labor_cost, material_cost, estimated_days, proposal_notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(body["job_id"]),
            body.get("contractor_id", 1),
            body["contractor_name"],
            body["contractor_email"],
            body.get("contractor_phone", ""),
            amount,
            fee,
            payout,
            float(body.get("labor_cost", 0)),
            float(body.get("material_cost", 0)),
            int(body.get("estimated_days", 1)),
            body["proposal_notes"],
            "pending"
        ))
        bid_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.send_json({
            "success": True,
            "bid_id": bid_id,
            "platform_fee": fee,
            "contractor_payout": payout,
            "message": f"Bid submitted. Platform fee: 10% (${fee:.2f}). Net payout: ${payout:.2f}."
        }, 201)

    def handle_get_payouts(self, query):
        cid = query.get("contractor_id", [None])[0]
        conn = get_db()
        cursor = conn.cursor()
        if cid:
            cursor.execute("SELECT * FROM payouts WHERE contractor_id = ? ORDER BY created_at DESC", (cid,))
        else:
            cursor.execute("SELECT * FROM payouts ORDER BY created_at DESC")
        payouts = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.send_json({"payouts": payouts})

    def handle_create_review(self, body):
        required = ["job_id", "contractor_id", "rating"]
        for r in required:
            if r not in body:
                self.send_json({"error": f"Missing {r}"}, 400)
                return

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO reviews (job_id, client_id, contractor_id, rating, arrived_on_time, review_text)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            body["job_id"],
            body.get("client_id", 1),
            body["contractor_id"],
            float(body["rating"]),
            int(body.get("arrived_on_time", 1)),
            body.get("review_text", "")
        ))

        cid = body["contractor_id"]
        cursor.execute("SELECT AVG(rating) as avg_rating, AVG(arrived_on_time) * 100 as on_time_pct, COUNT(*) as review_count FROM reviews WHERE contractor_id = ?", (cid,))
        stats = cursor.fetchone()

        avg_rating = round(stats["avg_rating"] or 5.0, 2)
        on_time_pct = round(stats["on_time_pct"] or 100.0, 1)
        quality_score = round((avg_rating / 5.0) * 60 + (on_time_pct * 0.40), 1)

        badges = ["Top Rated Pro", "Verified License"]
        if on_time_pct >= 95: badges.append("100% On-Time Dispatch")

        cursor.execute("""
        UPDATE contractors
        SET rating = ?, on_time_rate = ?, quality_score = ?, badges = ?
        WHERE id = ?
        """, (avg_rating, on_time_pct, quality_score, ", ".join(badges), cid))

        conn.commit()
        conn.close()

        self.send_json({
            "success": True,
            "rating": avg_rating,
            "on_time_rate": on_time_pct,
            "quality_score": quality_score,
            "message": "Review submitted and contractor scoring updated."
        })

    def handle_get_my_jobs(self, query):
        user_id = query.get("user_id", [None])[0]
        role = query.get("role", ["business"])[0]

        conn = get_db()
        cursor = conn.cursor()

        if role == "business":
            cursor.execute("""
            SELECT j.*, (SELECT COUNT(*) FROM bids WHERE job_id = j.id) as bid_count,
                   c.name as assigned_contractor_name, c.insurance_verified, c.is_pro_member
            FROM jobs j
            LEFT JOIN contractors c ON j.assigned_contractor_id = c.id
            WHERE j.client_id = ?
            ORDER BY j.created_at DESC
            """, (user_id,))
        else:
            cursor.execute("SELECT id FROM contractors WHERE user_id = ?", (user_id,))
            c_row = cursor.fetchone()
            cid = c_row["id"] if c_row else user_id

            cursor.execute("""
            SELECT DISTINCT j.*, (SELECT COUNT(*) FROM bids WHERE job_id = j.id) as bid_count,
                   b.id as my_bid_id, b.amount as my_bid_amount, b.status as my_bid_status,
                   b.counter_offer_amount, b.counter_offer_notes,
                   c.name as assigned_contractor_name, c.insurance_verified, c.is_pro_member
            FROM jobs j
            LEFT JOIN contractors c ON j.assigned_contractor_id = c.id
            LEFT JOIN bids b ON b.job_id = j.id AND b.contractor_id = ?
            WHERE j.assigned_contractor_id = ? OR b.contractor_id = ?
            ORDER BY j.created_at DESC
            """, (cid, cid, cid))

        jobs = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.send_json({"jobs": jobs, "count": len(jobs)})

    def handle_get_contractor_profile(self, cid):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contractors WHERE id = ?", (cid,))
        c = cursor.fetchone()
        conn.close()
        if not c:
            self.send_json({"error": "Contractor not found"}, 404)
        else:
            self.send_json({"contractor": dict(c)})

    def handle_get_contractors(self, query):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contractors ORDER BY quality_score DESC, rating DESC")
        contractors = [dict(row) for row in cursor.fetchall()]
        conn.close()
        self.send_json({"contractors": contractors, "count": len(contractors)})

    def handle_get_bids(self, query):
        job_id = query.get("job_id", [None])[0]
        if not job_id:
            self.send_json({"error": "job_id parameter required"}, 400)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bids WHERE job_id = ? ORDER BY amount ASC", (job_id,))
        bids = [dict(row) for row in cursor.fetchall()]
        conn.close()

        self.send_json({"bids": bids, "count": len(bids)})

    def handle_get_stats(self):
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as open_jobs FROM jobs WHERE status = 'published'")
        open_jobs = cursor.fetchone()["open_jobs"]

        cursor.execute("SELECT COUNT(*) as contractors_count FROM contractors")
        contractors_count = cursor.fetchone()["contractors_count"]

        cursor.execute("SELECT COUNT(*) as total_bids FROM bids")
        total_bids = cursor.fetchone()["total_bids"]

        cursor.execute("SELECT COALESCE(SUM(platform_fee), 0) as platform_earnings, COALESCE(SUM(gross_amount), 0) as completed_volume FROM payouts WHERE status = 'processed'")
        earnings_data = cursor.fetchone()

        cursor.execute("SELECT AVG(amount / NULLIF(drop_count, 0)) as avg_drop_price FROM bids b JOIN jobs j ON b.job_id = j.id WHERE j.drop_count > 0")
        avg_drop = cursor.fetchone()["avg_drop_price"] or 132.0

        conn.close()

        self.send_json({
            "open_jobs": open_jobs,
            "contractors_count": contractors_count,
            "total_bids": total_bids,
            "platform_earnings": round(earnings_data["platform_earnings"], 2),
            "completed_volume": round(earnings_data["completed_volume"], 2),
            "fee_percentage": PLATFORM_FEE_PCT,
            "pro_fee_percentage": PRO_FEE_PCT,
            "instant_debit_fee_percentage": INSTANT_DEBIT_FEE_PCT,
            "avg_price_per_drop": round(avg_drop, 2)
        })

def run_server(port=8080):
    init_db()
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, MarketplaceHandler)
    print(f"[*] VoltWire Enterprise Marketplace running on 0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
