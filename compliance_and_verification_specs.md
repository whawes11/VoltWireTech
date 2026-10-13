# VoltWire Compliance, Identity Verification & Insurance Specifications

This document outlines the legal compliance architecture, identity verification (KYC), tax documentation, insurance validation, and financial transaction requirements implemented in the VoltWire marketplace platform.

---

## 1. Legal & Tax Compliance Requirements (W-9 / 1099-NEC)

To operate legally as a two-sided field service marketplace in the United States and disburse electronic funds to independent service providers:

### Federal Tax Identification (W-9 Collection)
- **Mandatory Collection at Signup:** During contractor onboarding, service providers must select their legal business structure (LLC, S-Corp, C-Corp, or Sole Proprietorship) and submit their Federal Tax Identification Number.
- **Tax ID Formats:**
  - **Employer Identification Number (EIN):** Standard format `XX-XXXXXXX` for registered businesses.
  - **Social Security Number (SSN):** For unincorporated sole proprietors.
- **Form 1099-NEC Annual Reporting:** Under IRS regulations, any independent contractor earning over $600 in net payouts annually must receive an automated Form 1099-NEC at the end of the tax year. Masked tax identification numbers (`XX-XXX4192`) are stored securely in the database.

### Identity Verification (Know Your Customer / KYC)
- **Government-Issued Photo ID:** Technicians must submit a valid state driver's license or passport.
- **License & Accreditation:** State Low Voltage Unrestricted License (e.g., GA LVU) and BICSI / OSHA certifications are recorded on the contractor profile.

---

## 2. Mandatory General Liability Insurance Gate

In commercial low-voltage cabling, telecommunications, and CCTV installations, building owners and IT clients mandate proof of insurance before contractors touch physical infrastructure.

### Insurance Policy Validation Rules:
1. **Minimum Coverage Amount:** Contractors must carry an active Commercial General Liability policy with at least **$1,000,000 per occurrence** (with $2,000,000 aggregate recommended).
2. **Required Certificate of Insurance (COI) Details:**
   - Admitted Insurance Carrier Name (e.g., Travelers, Hartford, Hiscox, Next Insurance)
   - Commercial Policy Number
   - Expiration Date
3. **Automated Escrow Payment Gate:**
   - When an IT client approves a completed work order, the platform's settlement engine automatically queries the contractor's `insurance_verified` flag.
   - **Enforcement Rule:** If a contractor's insurance policy is missing, unverified, or expired, the payout is automatically tagged as `held_insurance_required`.
   - Funds remain securely in escrow until a valid Certificate of Insurance is verified.

---

## 3. Financial Settlement & Payout Engine

VoltWire handles funds through an escrow architecture:

### 1. Standard 10.0% Marketplace Take-Rate
- When a client creates or approves a work order (e.g., $1,000.00), the platform automatically calculates:
  - **Gross Work Order Total:** $1,000.00
  - **VoltWire 10% Platform Fee:** $100.00
  - **Base Contractor Share (90%):** $900.00

### 2. Disbursal Methods
- **Standard Bank ACH Direct Deposit (Free):**
  - Paid out via bank routing and account number.
  - Standard banking clearance: 3 to 5 business days post-approval.
- **Instant Direct Pay to Debit Card (+1.5% Expedited Fee):**
  - Instant transfer via debit card payment rails.
  - A 1.5% processing fee (e.g., $13.50 on a $900 payout) is deducted from the technician's payout to cover debit card network fees.
  - Funds arrive within minutes of client approval.
- **VoltWire Pro Membership Tier (+2.0% Work Order Fee):**
  - Provides **0-Day Instant Processing** with zero clearance waiting period immediately after client approval.
  - Deducts a 2.0% Pro fee from the work order.

---

## 4. App Store & Google Play Store Compliance Guidelines

When submitting VoltWire to Apple and Google:

1. **Apple App Store Review Guidelines (Section 3.1.3(e) - Goods and Services Outside the App):**
   - Because VoltWire facilitates physical, real-world low-voltage field labor (cabling, camera installations, network hardware setup), Apple's 30% in-app purchase (IAP) tax **does not apply**.
   - Physical B2B field services are permitted to use third-party payment gateways (such as Stripe Connect) directly inside the mobile app.
2. **Google Play Store Policy (Physical Services Exemption):**
   - Google Play Billing is strictly required only for digital goods (in-game items, digital media). Physical field service dispatch marketplaces are explicitly exempt and use external payment processing.
3. **Data Security & Privacy:**
   - Banking numbers and debit card numbers are tokenized via payment gateway APIs, storing only masked references (`last4`) in the local application database.
