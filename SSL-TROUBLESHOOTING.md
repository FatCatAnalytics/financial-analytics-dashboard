# 🔒 SSL Certificate Troubleshooting Guide

## Common SSL Issues on New Machines

### ❌ **Error: "Unable to get issuer certificate"**

This error typically occurs when:
- System certificates are outdated
- Corporate firewall/proxy interferes with SSL
- Node.js or Python can't verify SSL certificates

---

## 🛠️ **Quick Fixes**

### **Option 1: Use the Development Startup Script**
```bash
./start-dev.sh
```
This script automatically handles SSL issues for development.

### **Option 2: Manual Environment Variables**

**For Frontend (Node.js):**
```bash
export NODE_TLS_REJECT_UNAUTHORIZED=0
cd frontend
npm run dev
```

**For Backend (Python):**
```bash
export PYTHONHTTPSVERIFY=0
source .venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### **Option 3: Update System Certificates**

**macOS:**
```bash
# Update certificates
brew install ca-certificates
# Or update all packages
brew update && brew upgrade
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ca-certificates
```

### **Option 4: Python-specific Fixes**

**Install/Update Certificate Bundle:**
```bash
pip install --upgrade certifi requests urllib3
```

**For conda environments:**
```bash
conda install certifi
```

---

## 🏢 **Corporate Network Issues**

If you're on a corporate network:

1. **Set Proxy Variables:**
```bash
export HTTPS_PROXY=http://your-proxy:port
export HTTP_PROXY=http://your-proxy:port
```

2. **Configure npm for corporate proxy:**
```bash
npm config set proxy http://your-proxy:port
npm config set https-proxy http://your-proxy:port
npm config set strict-ssl false
```

3. **Configure pip for corporate proxy:**
```bash
pip config set global.trusted-host pypi.org
pip config set global.trusted-host pypi.python.org
pip config set global.trusted-host files.pythonhosted.org
```

---

## 🔍 **Diagnostic Commands**

**Check SSL Version:**
```bash
python -c "import ssl; print('SSL Version:', ssl.OPENSSL_VERSION)"
```

**Test Certificate Verification:**
```bash
python -c "import requests; print(requests.get('https://httpbin.org/get').status_code)"
```

**Check Node.js Version:**
```bash
node --version
npm --version
```

---

## ✅ **Verification Steps**

After applying fixes:

1. **Test Backend:**
```bash
curl http://localhost:8000/health
```

2. **Test Frontend:**
Open browser to `http://localhost:3000`

3. **Test API Integration:**
Check if dashboard loads data without errors

---

## 🚨 **Security Note**

**⚠️ IMPORTANT:** The SSL verification disable flags (`NODE_TLS_REJECT_UNAUTHORIZED=0`, `PYTHONHTTPSVERIFY=0`) should **ONLY** be used in development environments.

**Never use these in production!**

For production deployments:
- Use proper SSL certificates
- Configure certificate authorities correctly
- Enable all SSL verification
