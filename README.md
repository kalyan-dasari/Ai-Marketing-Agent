# Project-to-Reach

A personal, local-first marketing workspace for turning software projects into reviewed, platform-specific campaign drafts.

## Quick start

Python 3.10+ is recommended. From this folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open <http://127.0.0.1:5000>. Data is stored in `project_to_reach.sqlite3` next to `run.py` and survives restarts. The server binds to loopback only.

## Phase 1 features

- Add projects with a description and optional website and repository links.
- Generate deterministic offline LinkedIn founder story, Instagram Reel outline, and Reddit feedback request drafts.
- Select campaign objective, audience, length, tone, and platforms.
- Edit content, preserve prior copy, and return edited approved assets to review.
- Approve or reject drafts. Approval is required before queue/publish states; publishing integrations are not configured and no post is sent.
- SQLite relational schema includes campaign, source, scheduled post, metric, experiment, distribution target, and audit tables for incremental work.
- Responsive dashboard with projects, campaign setup, review queue, draft status, and campaign overview.

## API

Versioned endpoints are under `/api/v1`: `GET/POST /projects`, `GET/POST /campaigns`, `GET /assets`, `PATCH /assets/<id>`, and `POST /assets/<id>/status`.

The mock provider does not fetch URLs, execute uploaded content, or invent product capabilities, customer results, or metrics. The Instagram walkthrough is a structure that must be filled with verified on-screen steps. Reddit posts are drafts for manual adaptation after checking community rules.

## Not configured yet

URL/GitHub ingestion, README uploads, local LLM provider, authenticated multi-user access, publishing integrations, background scheduling, analytics entry UI, and external tracking are future phases. Do not expose this development app publicly without authentication, CSRF protection, and deployment hardening.
