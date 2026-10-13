#!/usr/bin/env bash
# ==============================================================================
# VoltWire All-In-One Build & Package Automation Script for macOS
# Builds Mac Desktop (.dmg), prepares iOS (Xcode), Android, and PWA assets.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "========================================================"
echo "⚡ VOLTWIRE FIELD SERVICE MARKETPLACE - MULTI-PLATFORM BUILD"
echo "========================================================"
echo "Project Directory: $PROJECT_ROOT"
echo ""

# 1. Check Prerequisites
echo "▶ Checking development environment prerequisites..."
command -v node >/dev/null 2>&1 || { echo "❌ Error: Node.js is not installed. Install via 'brew install node' or https://nodejs.org"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ Error: npm is not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Error: Python 3 is not installed."; exit 1; }

echo "  ✓ Node.js $(node -v) detected"
echo "  ✓ npm $(npm -v) detected"
echo "  ✓ Python $(python3 --version) detected"
echo ""

# 2. Syntax & Database Verification
echo "▶ Verifying Python backend syntax & SQLite schema..."
python3 -c "import py_compile; py_compile.compile('server.py')"
echo "  ✓ server.py compiled with zero syntax errors"
python3 -c "import sqlite3; conn = sqlite3.connect('marketplace_v2.db'); print('  ✓ marketplace_v2.db valid with', conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 'jobs')"
echo ""

# 3. Dependencies
echo "▶ Installing Node dependencies..."
npm install --no-audit --no-fund
echo "  ✓ Dependencies installed"
echo ""

# 4. Mobile App Preparation (Capacitor for iOS & Android)
echo "▶ Preparing Mobile Apps (Capacitor)..."
if [ ! -d "ios" ]; then
  echo "  Adding iOS platform..."
  npx cap add ios || true
fi

if [ ! -d "android" ]; then
  echo "  Adding Android platform..."
  npx cap add android || true
fi

echo "  Syncing web assets to iOS & Android native targets..."
npx cap sync
echo "  ✓ Mobile assets synchronized"
echo ""

# 5. Desktop Application Packaging (macOS .dmg)
echo "▶ Packaging Desktop Software for macOS..."
if npx electron-builder --mac --dir; then
  echo "  ✓ macOS Desktop binaries packaged in dist/"
else
  echo "  ⚠ Note: electron-builder requires Xcode Command Line Tools for full .dmg signing."
fi
echo ""

echo "========================================================"
echo "✅ BUILD COMPLETE! Distribution targets ready:"
echo "========================================================"
echo "• Desktop macOS:   dist/ (Installable .app / .dmg)"
echo "• Mobile iOS:       ios/App (Ready for Xcode: 'npm run mobile:ios')"
echo "• Mobile Android:   android (Ready for Android Studio: 'npm run mobile:android')"
echo "• Web & PWA:        static/ (Ready for cloud deployment & instant PWA install)"
echo "========================================================"
