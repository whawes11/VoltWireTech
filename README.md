# VoltWire - Field Service Dispatch & Subcontracting Marketplace

VoltWire is an on-demand B2B commercial field service marketplace modeled after Field Nation and WorkMarket, built specifically for the low-voltage structured cabling, 4K CCTV/IP surveillance, access control, and network infrastructure industry.

---

## ⚡ Revenue & Monetization Model

VoltWire has multiple built-in revenue streams:
1. **10.0% Standard Marketplace Take-Rate:** Automatically deducted from every completed and approved work order.
2. **Pro Membership Tier (+2.0% per Work Order / $49/mo):** Technicians receive **0-Day Instant Escrow Processing** immediately upon client approval, bypassing the standard 3–5 day ACH waiting period.
3. **Expedited Debit Card Payout Fee (1.5%):** Non-pro contractors who want immediate payout to their debit card pay a 1.5% expedited transfer fee.
4. **Direct Client Work Order Posting:** Enterprise IT clients post open contracts with verified technician dispatch.

---

## 🗺️ Georgia Interactive Dispatch Radar Map

VoltWire includes a high-contrast dark mode interactive dispatch map powered by Leaflet:
* **Real-Time Job Pins:** Automatically plots commercial work order locations across Georgia (Atlanta Metro, Alpharetta, Marietta, Duluth, Savannah, Macon, Augusta).
* **Multi-View Modes:** Instantly switch between **List View**, **Georgia Dispatch Radar Map**, and side-by-side **Split View**.
* **Interactive Bidding:** Clicking any map pin opens a work order summary card with one-click access to the subcontract bidding modal.
* **Category Sync:** Filtering by discipline (CCTV, Network Hardware, Structured Cabling, Fiber Optics, Access Control) dynamically updates both the list and map pins.

---

## 🛡️ Legal & Compliance Verification

Every service provider undergoes automated compliance onboarding:
* **W-9 & Tax Identification:** Automated collection of Federal EIN or SSN with entity classification (LLC, S-Corp, Sole Proprietorship).
* **Mandatory General Liability Insurance Gate:** Contractors must provide their insurance carrier, policy number, expiration date, and minimum **$1,000,000 per occurrence limit**. *Payments are held in escrow if insurance is expired or unverified.*
* **Identity & Licensing:** State Low Voltage License # (e.g. GA LVU) verification.

---

## 📱 Cross-Platform Architecture: Web, Mobile, Desktop & MAMP

VoltWire is engineered to be built, tested, and published across all environments:

### 1. Web & Cloud Hosting
- Run directly with Python:
  ```bash
  python3 server.py
  ```
  Access at `http://127.0.0.1:8080`.

### 2. MAMP & Local Server Integration
- **MAMP Reverse Proxy:** Use `mamp_config/httpd-voltwire.conf` to route traffic from MAMP's Apache web server to VoltWire's backend.
- **Instant Live Publishing Tunnel:** Run `scripts/start_live_tunnel.sh` to create an immediate public HTTPS URL for external testing via Cloudflare Tunnel or ngrok without opening router ports:
  ```bash
  bash scripts/start_live_tunnel.sh 8080
  ```

### 3. Mac Desktop Packaging (macOS .dmg)
- Test locally with Electron:
  ```bash
  npm run desktop
  ```
- Build macOS `.dmg` and `.app` installers:
  ```bash
  npm run desktop:build
  ```

### 4. Mobile Apps (Apple App Store & Google Play)
- Prepare and sync mobile assets:
  ```bash
  npm run mobile:prepare
  ```
- Open native iOS project in Xcode (ready for App Store submission):
  ```bash
  npm run mobile:ios
  ```
- Open native Android project in Android Studio (ready for Google Play submission):
  ```bash
  npm run mobile:android
  ```

### 5. Automated All-In-One Mac Build
- Execute all platform packaging tasks in a single command:
  ```bash
  npm run build:all
  ```

---

## 📂 Project Structure

```
low_voltage_marketplace/
├── server.py              # REST API & Escrow Settlement Engine
├── marketplace_v2.db      # SQLite database with compliance & payout records
├── capacitor.config.json  # Mobile app configuration for iOS & Android
├── electron-main.js       # Desktop app wrapper for macOS & Windows
├── package.json           # Multi-platform build scripts & dependencies
├── README.md              # Documentation & deployment instructions
├── compliance_and_verification_specs.md # W-9, COI, and store policy specs
├── scripts/
│   ├── build_all_platforms.sh # All-in-one Mac packaging & compilation script
│   └── start_live_tunnel.sh   # Instant public HTTPS tunnel launcher
├── mamp_config/
│   └── httpd-voltwire.conf    # MAMP / Apache reverse proxy configuration
└── static/
    ├── index.html         # High-contrast Dark Mode SPA with Dispatch Map
    ├── style.css          # Dark Mode styling, Leaflet overrides, responsive layout
    ├── app.js             # Client state, map rendering, negotiation & payouts
    └── manifest.json      # Mobile PWA manifest
```
# voltwire
# voltwire
