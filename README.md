# TradeIQ Market Analyzer

> **FastAPI** service that analyzes Indian market data for a given sector and returns structured trade-opportunity insights.
> Now fully equipped with a **Premium Interactive Dashboard**, **Live Charting**, **Native PDF Exports**, and **SMTP Email Delivery**!

---

## 🌟 Key Features

1. **Interactive Frontend Dashboard** (`http://localhost:8000/`) featuring ultra-fast animated UI and responsive design.
2. **AI-Powered Reports**: Hooks directly into Google Gemini (`gemini-1.5-flash`) for live, accurate sector trends, opportunities, and risk assessment tasks.
3. **Download Capabilities**: Native `.pdf` document printing and raw Markdown `.md` export tools built into the browser UI.
4. **Email Delivery System**: Real-time SMTP authentication to privately dispatch generated reports directly to a specified inbox.
5. **Secure Backend architecture**:
   - `X-API-Key` verification header.
   - Intelligent sliding-window Memory Rate Limiting (5 requests / 60 seconds).
   - Strict regex string sanitization for API safety.

---

## 📁 Project Structure

```text
JOB/
├── main.py                   # FastAPI app + Core Routing Endpoint bindings
├── static/
│   └── index.html            # The Interactive Frontend Dashboard
├── services/
│   ├── data_collection.py    # DuckDuckGo market data fetcher
│   └── ai_analysis.py        # Gemini Markdown generation and fallback mocks
├── utils/
│   ├── auth.py               # API-key authentication logic
│   ├── rate_limiter.py       # Security middleware
│   └── email_sender.py       # Python SMTP mail delivery logic
├── requirements.txt          # Python dependencies
└── .env                      # Live app secrets & SMTP configuration
```

---

## 🚀 Setup Instructions

### 1. Requirements
Ensure you are using **Python 3.11+**.

### 2. Install & Activate Env

```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install Dependencies
pip install -r requirements.txt
```

### 3. Environment Variable Configuration (`.env`)
Create or edit your `.env` file in the root folder with the following variables:

```ini
VALID_API_KEYS=dev-key-12345,admin-key-999
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# SMTP configuration for Email delivery functionality
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
# Use your direct email and app password here:
SMTP_USER=my_email_address@gmail.com
SMTP_PASS=my_gmail_app_password
```

*(Note: If valid SMTP credentials are not found, the server gracefully reverts to a local mockup to prevent frontend crashes).*

---

## 💻 Running the Application

Start the FastAPI application using Uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Server is active and accessible via **http://localhost:8000**.

---

## 📖 API Documentation

Access the interactive API sandboxes directly in your browser:
* **Interactive UI**: `http://localhost:8000/docs` (Swagger)
* **Readable Docs**: `http://localhost:8000/redoc`

### Terminal Usage (cURL)

```bash
# Fetch a Technology Sector Analysis
curl -X GET "http://localhost:8000/analyze/technology" \
     -H "X-API-Key: dev-key-12345"

# Directly trigger the Email dispatcher
curl -X POST "http://localhost:8000/api/send_email" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "sector": "technology", "report": "# Tech Trends..."}'
```

---

## 🔒 Security Model

- **Authentication**: Fully secured by `X-API-Key`.
- **Validation**: Strict boundary limits and character sanitization preventing remote-code injection.
- **Fail-safes**: Deep Exception catching and graceful UI fallbacks on Timeout or external API outages.
