# PocketSmart AI

PocketSmart AI is a student-friendly FastAPI + Jinja2 web application for budget-aware planning across **Home Interior**, **Party**, and **Jewelry** use cases. It follows the supplied project documentation: responsive blue/white UI, authentication, session-aware history, structured AI recommendations, optional jewelry image analysis, and safe demo/search links for external platforms.

The supplied documentation is internally mixed between Flask/FastAPI in early sections; the implementation follows the later concrete FastAPI architecture, as requested in the implementation brief.

## Features
- User registration/login/logout with hashed passwords and JWT-backed sessions
- Protected dashboard and recommendation history
- Home planner: rooms, lighting, ceiling fans, furniture/table quantities and preferences
- Party planner: budget, guests, event type, venue, catering, decoration and entertainment
- Jewelry planner: occasion/style/outfit description and optional JPG/PNG/WEBP image
- Gemini integration through the current `google-genai` SDK when `GEMINI_API_KEY` is configured
- Structured Pydantic validation and budget enforcement
- Graceful demo fallback when Gemini is unavailable
- Search links for Amazon, Flipkart, IKEA, Swiggy, Zomato and OYO; these are not claimed as live inventory
- SQLite persistence for users, sessions and recommendation history
- Automated tests

## Folder structure
```text
PocketSmart/
├── main.py
├── gemini_utils.py
├── database.py
├── schemas.py
├── auth.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── home_planner.html
│   ├── party_planner.html
│   ├── jewelry_planner.html
│   ├── history.html
│   ├── recommendation_details.html
│   └── recommendation_result.html
├── static/
│   ├── css/styles.css
│   ├── js/app.js
│   └── uploads/
└── tests/
```

## Windows + VS Code setup
Open the `PocketSmart` folder in VS Code Terminal.

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
```

If `python` is not recognized, use the full path to your installed Python, for example:
```powershell
C:\Program Files\Python313\python.exe -m venv .venv
```

## Configure `.env`
Open `.env` and set:
```env
GEMINI_API_KEY=your_google_ai_api_key
GEMINI_MODEL=gemini-2.5-flash
SECRET_KEY=use-a-long-random-secret
DATABASE_URL=sqlite:///pocketsmart.db
ACCESS_TOKEN_EXPIRE_MINUTES=60
MAX_UPLOAD_MB=5
```

Do not commit `.env` to Git. Never paste a real API key into Python source files.

## Gemini setup
Create a Gemini API key through Google's current Gemini/AI Studio developer tooling, then place it in `GEMINI_API_KEY`. The model is read from `GEMINI_MODEL`, so you can change it without editing application code.

If the key is empty or Gemini is temporarily unavailable, the app uses clearly labelled demo fallback recommendations. This keeps the student project runnable without pretending that external data is live.

## Database
No separate database server is required. The application creates `pocketsmart.db` automatically on startup.

Tables:
- `users`
- `sessions`
- `recommendations`

## Run
```powershell
.venv\Scripts\activate
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open: **http://127.0.0.1:8000**

## Test
```powershell
python -m pytest -q
```

Syntax/import smoke check:
```powershell
python -m compileall .
```

## Manual test procedure
1. Open `/register` and create an account.
2. Confirm the dashboard opens after registration.
3. Open Home Budget Planner and submit a budget.
4. Check allocation, items, prices, remaining budget and shopping links.
5. Open Party Budget Planner and submit a guest/event scenario.
6. Open Jewelry Budget Planner and submit an occasion/style; optionally upload a JPG/PNG/WEBP image.
7. Open History and select a recommendation.
8. Log out and verify protected pages redirect/error until you log in again.

## Backend routes
- `GET /` home page
- `GET /dashboard`
- `GET /home-planner`
- `GET /party-planner`
- `GET /jewelry-planner`
- `GET /login`, `POST /login`
- `GET /register`, `POST /register`
- `POST /logout`
- `POST /token`
- `POST /generate-home`
- `POST /generate-party`
- `POST /generate-jewelry`
- `GET /session-info`
- `GET /session-data`
- `GET /history`, `GET /history-data`
- `GET /recommendations-details/{recommendation_id}`
- `GET /recommendations-details?recommendation_id=...`
- `GET /startup`

## External integrations
**Real in this implementation:** Gemini API when a valid key/model is configured.

**Demo/search-link integrations:** Amazon, Flipkart, IKEA, Swiggy, Zomato and OYO. The documentation mentions these platforms, but the project does not claim unauthorized live APIs or scraping. Links are safe search links and demo prices are labelled as such.

## Budget enforcement
The backend validates positive budgets, quantities and item prices. Generated item totals are normalized so displayed recommendations do not exceed the user's requested budget.

## Known limitations
- Search links open external search pages rather than returning verified real-time inventory.
- Demo fallback prices are illustrative, not current market prices.
- Gemini behavior depends on the configured model, account limits and API availability.
- SQLite is appropriate for this student/demo deployment; production multi-user hosting would normally use a managed database.
