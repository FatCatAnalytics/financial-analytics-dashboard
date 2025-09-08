# 📦 Offline Installation Guide

This guide explains how to deploy the Financial Analytics Dashboard in environments without internet access (corporate networks, air-gapped systems, etc.).

## 🎯 Overview

The offline installation process involves two steps:
1. **Bundle dependencies** (on a machine with internet access)
2. **Install offline** (on the target machine without internet)

---

## 📋 Prerequisites

### Source Machine (with internet):
- Python 3.8+
- Node.js 18+
- npm
- Git (to clone the repository)

### Target Machine (without internet):
- Python 3.8+
- Node.js 18+
- No internet connection required

---

## 🔄 Step 1: Bundle Dependencies (Internet Required)

Run this on a machine with internet access:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/financial-analytics-dashboard.git
cd financial-analytics-dashboard

# Bundle all dependencies
./bundle-dependencies.sh
```

This creates:
- `offline-deps/` directory with all dependencies
- `financial-dashboard-offline-deps.tar.gz` (portable archive)

### What Gets Bundled:

**Python Dependencies:**
- All wheel files (.whl) for backend packages
- FastAPI, Polars, Pandas, NumPy, etc.
- Stored in: `offline-deps/python-wheels/`

**Node.js Dependencies:**
- Complete node_modules directory
- React, Next.js, Tailwind CSS, Recharts, etc.
- Stored in: `offline-deps/node_modules/`

---

## 🚀 Step 2: Transfer to Target Machine

### Option A: Copy Directory
```bash
# Copy the entire project including offline-deps
scp -r financial-analytics-dashboard/ user@target-machine:/path/to/destination/
```

### Option B: Use Archive
```bash
# Download from GitHub Releases
wget https://github.com/FatCatAnalytics/financial-analytics-dashboard/releases/download/v1.0.0-offline-bundle/financial-dashboard-offline-deps.tar.gz

# Or use the download script
./download-bundle.sh

# Extract
tar -xzf financial-dashboard-offline-deps.tar.gz
```

---

## 💻 Step 3: Install Offline (No Internet Required)

On the target machine:

```bash
cd financial-analytics-dashboard

# Run offline installation
./install-offline.sh
```

The script will:
1. ✅ Create Python virtual environment
2. ✅ Install Python packages from local wheels
3. ✅ Setup Node.js dependencies from bundled modules
4. ✅ Build frontend for production
5. ✅ Create configuration templates
6. ✅ Verify all installations

---

## 🏃‍♂️ Step 4: Run the Application

```bash
# Start both backend and frontend
./start-dev.sh
```

Or manually:
```bash
# Terminal 1 - Backend
source .venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

**Access URLs:**
- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🔧 Corporate Environment Setup

### Proxy Configuration

If your corporate network requires proxy settings:

**For npm:**
```bash
npm config set proxy http://proxy.company.com:8080
npm config set https-proxy http://proxy.company.com:8080
npm config set strict-ssl false
```

**For pip:**
```bash
pip config set global.proxy http://proxy.company.com:8080
pip config set global.trusted-host pypi.org
pip config set global.trusted-host pypi.python.org
```

### SSL Certificate Issues

The application includes SSL troubleshooting:
- See `SSL-TROUBLESHOOTING.md` for detailed solutions
- Use `start-dev.sh` which automatically handles SSL bypass for development

---

## 📁 Directory Structure After Installation

```
financial-analytics-dashboard/
├── offline-deps/                    # Bundled dependencies
│   ├── python-wheels/              # Python wheel files
│   ├── node_modules/               # Node.js modules
│   └── BUNDLE_INFO.md              # Bundle information
├── .venv/                          # Python virtual environment
├── frontend/
│   ├── node_modules/               # Installed from offline bundle
│   └── .next/                      # Built application
├── main.py                         # Core backend logic
├── api.py                          # FastAPI server
├── start-dev.sh                    # Development startup script
├── install-offline.sh              # Offline installation script
├── bundle-dependencies.sh          # Dependency bundling script
└── .env                            # Configuration file
```

---

## 🐛 Troubleshooting

### Common Issues:

**1. Permission Denied**
```bash
chmod +x *.sh
```

**2. Python Virtual Environment Issues**
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
```

**3. Node.js Version Conflicts**
```bash
# Use Node Version Manager if available
nvm use 18
```

**4. SSL Certificate Errors**
```bash
export NODE_TLS_REJECT_UNAUTHORIZED=0
export PYTHONHTTPSVERIFY=0
```

### Verification Commands:

**Check Python Installation:**
```bash
source .venv/bin/activate
python -c "import fastapi, polars, pandas; print('✅ Python OK')"
```

**Check Node.js Installation:**
```bash
cd frontend
node -e "console.log('✅ Node.js OK')"
```

**Check Application Health:**
```bash
curl http://localhost:8000/health
curl -I http://localhost:3000
```

---

## 📊 Bundle Size Information

Typical bundle sizes:
- **Python wheels**: ~60-80 MB
- **Node.js modules**: ~200-300 MB
- **Total archive**: ~250-350 MB compressed

The exact size depends on your system architecture and dependency versions.

---

## 🔄 Updating Dependencies

To update the offline bundle:

1. **On internet machine:**
   ```bash
   # Update dependencies
   pip install -r requirements.txt --upgrade
   cd frontend && npm update && cd ..
   
   # Re-bundle
   ./bundle-dependencies.sh
   ```

2. **Transfer new bundle to target machine**

3. **Reinstall on target machine:**
   ```bash
   ./install-offline.sh
   ```

---

## 🛡️ Security Considerations

### Development vs Production:

**Development (current setup):**
- SSL verification disabled for convenience
- Debug mode enabled
- Development server (not production-ready)

**For Production Deployment:**
- Enable SSL verification
- Use proper SSL certificates
- Use production WSGI server (gunicorn)
- Set up reverse proxy (nginx)
- Configure firewall rules

### Environment Variables:
```bash
# Production settings
export NODE_ENV=production
export PYTHONHTTPSVERIFY=1
unset NODE_TLS_REJECT_UNAUTHORIZED
```

---

## 📞 Support

If you encounter issues:

1. Check `SSL-TROUBLESHOOTING.md`
2. Review `offline-deps/BUNDLE_INFO.md`
3. Run verification commands above
4. Check system requirements match bundle

---

## ✅ Quick Checklist

**Before bundling (internet machine):**
- [ ] Python 3.8+ installed
- [ ] Node.js 18+ installed
- [ ] All dependencies install successfully
- [ ] Application runs correctly

**After offline installation:**
- [ ] Python virtual environment created
- [ ] All Python packages installed from wheels
- [ ] Node.js modules copied successfully
- [ ] Application starts without errors
- [ ] Dashboard accessible at http://localhost:3000
- [ ] API responds at http://localhost:8000/health

**Ready for corporate deployment! 🎉**
