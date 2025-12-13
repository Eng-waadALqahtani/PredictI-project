# PredictAI - Digital Threat Fingerprint System

A full-stack security system that detects and fingerprints digital threats using machine learning and behavioral analysis.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Flask
- scikit-learn

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the backend server:
```bash
cd backend
python main.py
```

The server will run on `http://localhost:5000`

### Frontend

Open `frontend/public/index.html` in your browser or navigate to:
- Health Portal: `http://localhost:5000`
- Dashboard: `http://localhost:5000/dashboard.html`

## 📁 Project Structure

```
backend/
  ├── main.py          # Flask API server
  ├── engine.py        # Threat detection engine
  ├── models.py        # Data models
  └── storage.py       # In-memory storage

frontend/
  ├── public/          # HTML pages
  └── js/              # JavaScript files

ml/
  └── models/          # ML model files
```

## 🔧 API Endpoints

- `POST /api/v1/event` - Send security event
- `GET /api/v1/fingerprints` - Get all threat fingerprints
- `POST /api/v1/check-and-login` - Check user threat status
- `POST /api/v1/unblock-user` - Unblock a user
- `POST /api/v1/confirm-threat` - Confirm a threat
- `DELETE /api/v1/delete-fingerprint/:id` - Delete a fingerprint

## 🌐 Deployment

This project is configured for deployment on Render. See `render.yaml` for configuration.

## 📝 License

MIT License

