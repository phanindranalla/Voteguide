# VoteGuide 🗳️
> Interactive Election Process Education Assistant

**Live Demo**: [YOUR_CLOUD_RUN_URL_HERE]

---

## Challenge Vertical
Election Process Education — Helping citizens understand the democratic process through an interactive, accessible, and multilingual web assistant.

---

## Problem Statement
Many citizens lack a clear understanding of how elections work, leading to disengagement from the democratic process. Existing resources are often too complex, politically biased, or inaccessible to non-English speakers. VoteGuide addresses this gap by providing a structured, neutral, and interactive education platform covering all 8 universal stages of an election.

---

## Approach and Logic

VoteGuide uses a three-layer approach:

**1. Structured Content Layer**
Election knowledge is broken into 8 universal stages, role definitions, a 30-term glossary, and a 10-question quiz — stored as structured JSON for fast, cacheable API delivery. Cache-Control headers on static endpoints reduce redundant processing.

**2. AI Reasoning Layer**
Gemini 2.0 Flash powers a politically neutral chat assistant. The system prompt enforces impartiality — VoteGuide never endorses parties or candidates. Context-aware stage detection automatically links chat responses to relevant content panels, creating a connected learning experience.

**3. Accessibility and Language Layer**
Google Translate API enables responses in 8 languages. Full ARIA compliance ensures screen-reader usability. The 10-question quiz uses server-side answer validation — correct answers are never exposed to the client, preventing cheating while reinforcing learning through active recall.

---

## How the Solution Works

1. User opens the VoteGuide URL on any device
2. Dashboard loads with 5 tabs: Timeline, Stages, Who Does What, Glossary, and Quiz
3. User selects their preferred language from the header dropdown
4. User explores content tabs interactively — expanding stage cards, searching the glossary, or taking the quiz
5. User asks a natural language question in the chat panel — Gemini responds with a concise, neutral answer
6. If the answer relates to a specific stage, a clickable chip appears linking directly to that stage card in the dashboard

---

## Architecture

```
User Browser (index.html)
        ↓
FastAPI Application (main.py)
        ├── GET  /api/stages    → tools.py → election_stages.json
        ├── GET  /api/timeline  → tools.py → timeline.json
        ├── GET  /api/roles     → tools.py → roles.json
        ├── GET  /api/glossary  → tools.py → glossary.json
        ├── GET  /api/quiz      → tools.py → quiz.json (answers hidden)
        ├── POST /api/quiz/check→ tools.py → server-side validation
        ├── POST /api/chat      → agent.py → Gemini 2.0 Flash API
        │                                  → Google Translate API
        └── GET  /static        → index.html

Deployed on Google Cloud Run
```

---

## Google Services Used

| Service | Purpose | Implementation |
|---|---|---|
| Gemini 2.0 Flash | Powers AI chat assistant with political neutrality | agent.py |
| Google Translate API | Multilingual support in 8 languages | main.py /api/chat |
| Google Cloud Run | Hosts the deployable web application | Dockerfile |
| Google Fonts (Inter) | Clean readable typography | index.html CDN |
| Google Material Icons | Accessible UI icon system | index.html CDN |

---

## Features

- Interactive 8-stage election process timeline
- Expandable stage cards with citizen action guidance
- Role explorer covering Voter, Candidate, Election Commission, and Observer
- Searchable A-Z election glossary with 30+ terms
- 10-question interactive quiz with server-side answer validation (correct answers never sent to client)
- Gemini-powered multilingual chat assistant
- Politically neutral by design — enforced via system prompt
- Auto-suggests relevant stages based on chat context with clickable navigation chips
- Responds in 8 languages via Google Translate API
- Fully ARIA compliant — keyboard navigable, screen-reader friendly
- Mobile responsive — works on any device

---

## Setup and Deployment

### Prerequisites
- Python 3.11+
- Google Cloud account with billing enabled
- Gemini API key
- Google Translate API key (Cloud Translation API enabled in GCP Console)

### Local Development
```bash
git clone https://github.com/YOUR_USERNAME/voteguide
cd voteguide
cp .env.example .env
# Add your API keys to .env
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
# Open http://localhost:8080
```

### Quick Deploy
```bash
export GEMINI_API_KEY=your_gemini_key
export GOOGLE_TRANSLATE_API_KEY=your_translate_key
bash deploy.sh YOUR_PROJECT_ID us-central1
```

### Deploy to Google Cloud Run
```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/voteguide

gcloud run deploy voteguide \
  --image gcr.io/YOUR_PROJECT_ID/voteguide \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars \
    GEMINI_API_KEY=your_key,\
    GOOGLE_TRANSLATE_API_KEY=your_key
```

---

## Assumptions Made

1. Election stages represent a universal democratic process applicable to most countries — country-specific variations are not covered
2. Queue and crowd data is simulated via JSON — in production would connect to real civic APIs
3. Google Translate free tier used for demo — production would use service account auth
4. Quiz answers are validated server-side only — a deliberate security decision to prevent client-side inspection

---

## Testing

```bash
pytest tests/ -v
```

Test coverage includes:
- Stage data loading and sorting
- Glossary search (exact and partial match)
- Quiz answer validation (correct, wrong, invalid id)
- Security: quiz endpoint never exposes correct field
- Agent stage detection from natural language
- API endpoints: health check, input validation, message length limits

---

## Project Structure

```
voteguide/
├── main.py          # FastAPI app and all routes
├── agent.py         # Gemini chat agent
├── tools.py         # Data utility functions
├── data/
│   ├── election_stages.json
│   ├── timeline.json
│   ├── roles.json
│   ├── glossary.json
│   └── quiz.json
├── static/
│   └── index.html   # Complete frontend
├── tests/
│   └── test_tools.py
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
├── deploy.sh
└── README.md
```
