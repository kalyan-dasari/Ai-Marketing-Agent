# Project-to-Reach: Personal AI Marketing Agent

A personal, offline-first, zero-budget marketing workspace for software engineers and indie builders. Converts code repositories, project descriptions, and README documents into multi-channel campaigns across LinkedIn, Instagram, and Reddit with mandatory human-in-the-loop approval.

---

## 🚀 Key Highlights & Philosophy

- **Zero-Budget & Local-First (₹0):** Operates completely offline with a deterministic mock AI provider by default. Requires no paid API keys or external subscriptions.
- **Strict Ground Truth:** Never invents features, user numbers, testimonials, or performance metrics. All campaign copy is strictly derived from verified project details.
- **Human-in-the-Loop:** Safety-first architecture. Content cannot be published or queued without explicit human review and approval. Editing an approved draft automatically returns it to review.
- **SSRF & Upload Protection:** External URL ingestion and GitHub README fetching are protected against Server-Side Request Forgery (SSRF) by blocking loopback and private subnets.
- **Optional Local LLM:** Built-in adapter for local Ollama instances (`http://127.0.0.1:11434`) or OpenAI-compatible local endpoints (LM Studio, LocalAI) with seamless fallback to deterministic mock.

---

## 🛠 Architecture

```
project-to-reach/
├── app/
│   ├── __init__.py           # Flask app factory, config, and blueprint registration
│   ├── config.py             # Application settings & database path
│   ├── db.py                 # SQLite schema, indices, and auto-migrations
│   ├── models/               # Typed data structures (ProjectBrief, GeneratedAsset)
│   ├── providers/            # Modular AI provider architecture
│   │   ├── base.py           # Abstract BaseAIProvider interface
│   │   ├── mock.py           # Deterministic offline multi-angle provider
│   │   ├── local_llm.py      # Local Ollama / OpenAI-compatible endpoint provider
│   │   └── factory.py        # Provider factory reading workspace settings
│   ├── routes/
│   │   ├── api.py            # Versioned REST API (/api/v1) with validation
│   │   └── web.py            # Main application UI controller
│   ├── services/
│   │   ├── security.py       # SSRF validator, URL sanitizer, file extension checks
│   │   ├── project_service.py # Project CRUD, README upload, GitHub ingestion, brief analyzer
│   │   ├── campaign_service.py# Multi-angle generation, calendar scheduling, version history
│   │   ├── distribution_service.py # Community rules, manual sharing checklist
│   │   └── analytics_service.py  # Performance metrics recording & evidence-based learning
│   ├── static/
│   │   ├── app.js            # Single-page application router, modal handling, API calls
│   │   └── style.css         # Modern SaaS design system (DM Sans & Manrope)
│   └── templates/
│       └── index.html        # Responsive dashboard containing all 9 workspace views
├── tests/
│   └── test_workflow.py      # Automated unit and integration test suite
├── project_to_reach.sqlite3  # Persistent local SQLite database
├── requirements.txt          # Python dependencies
├── run.py                    # Local server runner
└── README.md                 # Complete documentation
```

---

## ⚡ Quick Start

### 1. Requirements
- Python 3.10+ (tested and running on Python 3.14)
- Web browser (Chrome, Firefox, Edge, Safari)

### 2. Installation & Running

```powershell
# From the project directory:
python run.py
```

Open your browser and navigate to:
**`http://127.0.0.1:5000`**

Data is automatically persisted in `project_to_reach.sqlite3` and survives server restarts. The development server binds strictly to loopback (`127.0.0.1`) for local security.

### 3. Running Automated Tests

```powershell
python -m unittest discover tests
```

---

## 📋 Workspace Views & Workflow

The web interface is organized into 9 views accessible via the sidebar:

| View | Purpose & Functionality |
| :--- | :--- |
| **◫ Overview** | Workspace health, quick stats (projects, campaigns, review queue, approved assets), recent projects, and quick actions. |
| **▤ Projects** | View projects, inspect normalized **Project Briefs** (Problem, Solution, UVP, Verified Features, Unknown Claims), upload README/Markdown files, and ingest public GitHub repositories. |
| **✳ Campaign Generator** | Configure campaign objectives, duration (7, 14, 30 days), target audience, tone, custom CTA, and platforms (LinkedIn, Instagram, Reddit). |
| **▧ Content Studio** | Browse all generated drafts. Filter by platform and status (`needs_review`, `approved`, `published`). One-click copy formatted text, trigger AI regeneration, view revision history diffs, and edit copy. |
| **✓ Approval Queue** | Focused triage interface displaying drafts requiring human review. Quick one-click **Approve**, **Reject**, or **Edit**. |
| **▦ Content Calendar** | Chronological schedule timeline mapping publication dates across the campaign duration with platform badges. |
| **◎ Distribution Tracker** | Manual sharing workflow for Reddit and developer communities. Includes anti-spam guidelines, community rules reminders, and tracking live post URLs. |
| **⌁ Analytics & Reach** | Log performance metrics (impressions, reach, engagements, link clicks, video views). Calculates engagement rates and CTR, generating evidence-based recommendations. |
| **⚙ Settings & AI** | Toggle between **Deterministic Mock Provider** and **Local LLM (Ollama)**. Configure Ollama host/port and model name with built-in **Test Connection** button and audit log inspector. |

---

## 🔒 Security & Safety Guarantees

1. **SSRF Prevention:**
   - Any external URL submitted for fetching (e.g. GitHub repos or website links) is checked against private IP spaces (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1`).
   - Requests to localhost or internal network infrastructure are strictly rejected.
2. **Untrusted Input Handling:**
   - Uploaded files are restricted to safe document formats (`.md`, `.markdown`, `.txt`, `.rst`) with a 2MB size ceiling.
   - Text is treated as untrusted data and never passed to a shell or executed.
3. **Mandatory Approval State Machine:**
   - States: `draft` → `needs_review` → `approved` → `queued` → `published` (or `rejected` / `failed`).
   - Unapproved drafts cannot be transitioned to `published` or `queued`.
   - Any modification to an `approved` asset automatically returns its status to `needs_review`.
4. **Audit Logging:**
   - All state changes, generation events, manual shares, and metric logs are recorded in the `audit_events` table for verification.

---

## 🔌 Integration Status

### ✅ Fully Implemented & Working:
- Local SQLite persistence with automated schema migrations.
- Complete multi-angle deterministic mock provider (Founder Stories, Architecture Lessons, Reel Scripts, Carousel Outlines, Feedback Requests, Build Logs).
- Ground-truth Project Brief extraction and normalization.
- Ingestion of markdown/text files and public GitHub repository READMEs.
- Interactive Content Studio with revision history diffs and regeneration.
- Human-in-the-loop approval workflow and status enforcement.
- Visual content calendar and scheduling roadmap.
- Reddit and developer community distribution tracking with live URL logging.
- Qualitative and quantitative metrics logging with evidence-based recommendation engine.
- Local LLM adapter for Ollama (`http://127.0.0.1:11434`) with connectivity testing.

### ⚠️ Deliberately Unconfigured (By Design for Zero-Budget MVP):
- **Automated Social Media Publishing APIs (LinkedIn / Instagram / Reddit APIs):** Social platforms frequently ban or restrict accounts using unverified third-party automated API posting without commercial app approval. Direct manual sharing with clipboard copy and live URL tracking is implemented to keep accounts safe and comply with terms of service.
- **Paid Cloud AI APIs (OpenAI, Anthropic):** Deliberately omitted to maintain ₹0 operational budget. Local Ollama and offline deterministic mock fulfill all intelligence requirements.
- **Multi-Tenant Authentication:** The application is architected as a local personal tool binding to `127.0.0.1`. Add reverse-proxy authentication (e.g. Nginx with basic auth or OAuth) before deploying to any public network.
