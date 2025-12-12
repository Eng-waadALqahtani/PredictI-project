# PredictIQ - Digital Threat Fingerprint
## Deployment Guide for Render

This guide will help you deploy the PredictIQ security system to Render.

---

## 📋 Prerequisites

- GitHub account
- Render account (free tier available)
- Python 3.10+

---

## 🚀 Deployment Steps

### 1. Prepare Your Repository

Ensure your repository contains:
- `backend/` - Backend Python files
- `frontend/` - Frontend HTML/JS files
- `ml/models/isoforest_absher.pkl` - ML model file
- `requirements.txt` - Python dependencies
- `render.yaml` - Render configuration
- `.gitignore` - Git ignore rules

### 2. Push to GitHub

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 3. Deploy on Render

1. **Log in to Render Dashboard**
   - Go to https://dashboard.render.com
   - Sign in with your GitHub account

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository containing PredictIQ

3. **Configure Service**
   - **Name**: `predictiq-backend`
   - **Environment**: `Python 3`
   - **Build Command**: (leave empty - Render will auto-detect)
   - **Start Command**: `python backend/main.py`
   - **Plan**: Free

4. **Environment Variables** (Optional)
   - `PYTHON_VERSION`: `3.10`
   - `PORT`: `5000` (Render sets this automatically)

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically:
     - Install dependencies from `requirements.txt`
     - Run the Flask application
     - Provide a public URL (e.g., `https://predictiq-backend.onrender.com`)

---

## 🔧 Configuration

### API Base URL

The frontend automatically detects the environment:
- **Production (Render)**: Uses `https://predictiq-backend.onrender.com`
- **Local Development**: Uses `http://localhost:5000`

This is configured in `frontend/js/events.js`:

```javascript
const isRender = window.location.hostname.includes("render") || 
                window.location.hostname.includes("onrender.com");

const API_BASE = isRender 
    ? "https://predictiq-backend.onrender.com"
    : `${window.location.protocol}//${window.location.hostname}:5000`;
```

### CORS Configuration

CORS is already configured in `backend/main.py` to allow all origins for `/api/*` routes:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

---

## 📁 Project Structure

```
hakathoon/
├── backend/
│   ├── main.py              # Flask app entry point
│   ├── engine.py            # Threat detection engine
│   ├── models.py            # Data models
│   ├── storage.py           # In-memory storage
│   └── tests/               # Unit tests (not deployed)
├── frontend/
│   ├── public/              # HTML pages
│   │   ├── index.html
│   │   ├── dashboard.html
│   │   ├── absher-login.html
│   │   ├── tawakkalna-login.html
│   │   └── health-portal.html
│   └── js/
│       └── events.js        # Centralized event tracking
├── ml/
│   └── models/
│       └── isoforest_absher.pkl  # ML model (~0.55 MB)
├── requirements.txt         # Python dependencies
├── render.yaml             # Render configuration
├── .gitignore              # Git ignore rules
└── README.md               # Project documentation
```

---

## ✅ Post-Deployment Checklist

- [ ] Service is running and accessible
- [ ] API endpoints respond correctly (`/api/v1/fingerprints`, `/api/v1/event`)
- [ ] Frontend pages load correctly
- [ ] Events are being sent and processed
- [ ] Threat fingerprints are being generated
- [ ] Dashboard displays fingerprints correctly

---

## 🧪 Testing

### Test API Endpoints

```bash
# Check service health
curl https://predictiq-backend.onrender.com/api/v1/debug

# Get fingerprints
curl https://predictiq-backend.onrender.com/api/v1/fingerprints

# Send test event
curl -X POST https://predictiq-backend.onrender.com/api/v1/event \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "login_attempt",
    "user_id": "test-user",
    "device_id": "test-device",
    "timestamp1": "2024-01-01T00:00:00Z"
  }'
```

### Test Frontend Pages

Visit these URLs after deployment:
- `https://predictiq-backend.onrender.com/` - Main hub
- `https://predictiq-backend.onrender.com/dashboard.html` - Dashboard
- `https://predictiq-backend.onrender.com/absher-login.html` - Absher login
- `https://predictiq-backend.onrender.com/tawakkalna-login.html` - Tawakkalna login

---

## 🔍 Troubleshooting

### Service Won't Start

1. **Check Logs**: View logs in Render dashboard
2. **Verify Requirements**: Ensure `requirements.txt` is correct
3. **Check Port**: Ensure `main.py` uses `os.environ.get('PORT', 5000)`

### CORS Errors

1. **Verify CORS Config**: Check `backend/main.py` CORS setup
2. **Check API Base URL**: Ensure `events.js` uses correct Render URL
3. **Test OPTIONS**: Verify OPTIONS requests are handled

### ML Model Not Found

1. **Verify Path**: Ensure `ml/models/isoforest_absher.pkl` exists
2. **Check Size**: Model should be < 20MB (currently ~0.55 MB)
3. **Git LFS**: If using Git LFS, ensure it's configured

---

## 📝 Notes

- **Free Tier Limitations**: Render free tier services spin down after 15 minutes of inactivity
- **Cold Start**: First request after spin-down may take 30-60 seconds
- **Storage**: Uses in-memory storage (data resets on restart)
- **ML Model**: Loaded from disk on startup (~0.55 MB)

---

## 🔗 Useful Links

- [Render Documentation](https://render.com/docs)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/latest/deploying/)
- [Project Documentation](./PROJECT_DOCUMENTATION.md)

---

## 📧 Support

For issues or questions:
1. Check Render logs
2. Review `PROJECT_DOCUMENTATION.md`
3. Check `TESTING_GUIDE.md` for testing procedures

---

**Last Updated**: 2024

