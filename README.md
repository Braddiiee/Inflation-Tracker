# Grocery Inflation Tracker

A local-first Streamlit app for tracking community-level grocery prices, normalizing units, and visualizing basket inflation—built for household budgeters, student researchers, and STEAM fair demos.

> **Status:** Project scaffold only. Application logic, database schema, and charts are not implemented yet.

---

## 1. Folder structure

```
Inflation Tracker/
├── app.py                  # Streamlit entry point (orchestration only)
├── requirements.txt        # Runtime dependencies
├── README.md               # This file
├── .gitignore
├── .env.example            # Future cloud DB credentials (optional)
├── data/
│   └── .gitkeep            # SQLite file created at runtime → data/tracker.db
├── src/
│   ├── __init__.py
│   ├── db_manager.py       # Data Access Layer (SQLAlchemy / SQLite)
│   ├── data_processor.py   # Pandas analytics & unit normalization
│   └── ui_components.py    # Reusable Streamlit widgets
├── pages/
│   ├── __init__.py
│   ├── home.py             # Dashboard & summary charts
│   ├── entry.py            # CRUD data entry form
│   └── analytics.py        # Filters & detailed visualizations
├── assets/
│   └── README.md           # Branding (e.g. logo.png) — add when ready
└── tests/
    ├── __init__.py
    └── .gitkeep            # Unit tests (DAL, inflation math)
```

---

## 2. File structure (quick reference)

| Path | Type |
|------|------|
| `app.py` | Entry |
| `requirements.txt` | Config |
| `README.md` | Docs |
| `.gitignore` | Config |
| `.env.example` | Config |
| `data/.gitkeep` | Placeholder |
| `src/db_manager.py` | Module |
| `src/data_processor.py` | Module |
| `src/ui_components.py` | Module |
| `pages/home.py` | View |
| `pages/entry.py` | View |
| `pages/analytics.py` | View |
| `assets/README.md` | Docs |
| `tests/__init__.py` | Test package |

---

## 3. Purpose of each file

| File | Why it exists |
|------|----------------|
| **`app.py`** | Single entry point Streamlit runs (`streamlit run app.py`). Wires pages, initializes `st.session_state`, and keeps the UI thin so database or chart libraries can change without rewriting views. |
| **`requirements.txt`** | Locks the MVP stack (Streamlit, Pandas, Plotly, SQLAlchemy) so judges and teammates get identical installs on any laptop. |
| **`README.md`** | Onboarding, architecture rationale, and workflow for a 6-week cycle; required for STEAM documentation. |
| **`.gitignore`** | Excludes virtualenvs, local `tracker.db`, secrets, and caches so only source is versioned. |
| **`.env.example`** | Documents future `DATABASE_URL` for PostgreSQL/cloud without committing real credentials. |
| **`data/`** | Holds the SQLite file (`tracker.db` created on first run). Separating data from code supports backup, reset, and later migration to a managed DB. |
| **`src/db_manager.py`** | **DAL:** all SQL and integrity rules live here. Prevents SQL injection via parameterized queries and isolates storage from Streamlit reruns. |
| **`src/data_processor.py`** | **Analytics:** normalized price (`price_total / quantity`), unit conversion (e.g. per 100 ml), and basket inflation %. UI and SQL stay unaware of Pandas details. |
| **`src/ui_components.py`** | **DRY UI:** shared sidebar filters, date pickers, and alert patterns so three pages stay consistent and “time to insight” stays under 5 seconds. |
| **`pages/home.py`** | **Budgeter persona:** dashboard with green/red trend cues and three MVP charts (trend, comparison, summary). |
| **`pages/entry.py`** | **CRUD:** manual entry for item, store, price, date, quantity, unit—MVP scope, no scrapers. |
| **`pages/analytics.py`** | **Analyst persona:** filters by date, store, category; line/bar charts from normalized data. |
| **`assets/`** | Optional branding (`logo.png`) without bloating the repo; referenced from sidebar when added. |
| **`tests/`** | Future pytest modules for `insert_price_record`, `calculate_inflation_rate`, and validation edge cases. |

### Planned internal API (implemented later in `src/`)

| Function | Returns | Layer |
|----------|---------|--------|
| `get_price_history(item_id, store_id)` | `DataFrame` | DAL → processor |
| `calculate_inflation_rate(item_id, start_date, end_date)` | `float` | processor |
| `insert_price_record(item_name, store_name, price, qty, unit)` | `bool` | DAL |

### Planned database tables (created in `db_manager.py` later)

- **`stores`** — `id`, unique `store_name`
- **`products`** — `id`, unique `product_name`, `category`
- **`price_logs`** — `product_id`, `store_id`, `price_total`, `quantity`, `unit_type`, `date_recorded`

---

## 4. Environment setup

### Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **Git** (optional but recommended)
- Standard laptop; no external database server for MVP

### One-time setup (Windows PowerShell)

```powershell
cd "c:\Users\HpVpro\Desktop\Inflation Tracker"

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Run (after logic is implemented)

```powershell
streamlit run app.py
```

Browser opens at `http://localhost:8501`. SQLite file will be created under `data/tracker.db` on first database initialization.

### Optional: execution policy

If activation fails on Windows:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 5. Dependency list

| Package | Role in MVP |
|---------|-------------|
| **streamlit** | UI layer, session state, multi-page app |
| **pandas** | Cleaning, normalized price, inflation aggregates |
| **plotly** | Interactive line (history) and bar (store compare) charts |
| **sqlalchemy** | ORM/Core API over SQLite; parameterized queries |

### Optional (later)

| Package | When |
|---------|------|
| **pydantic** | Strict form validation (negative price, future dates) |
| **pytest** | Automated tests in `tests/` |
| **ruff** | Lint/format in CI or pre-commit |

---

## 6. `requirements.txt`

See [`requirements.txt`](requirements.txt) in the project root. Install with:

```powershell
pip install -r requirements.txt
```

---

## 7. Development workflow

Aligned with a **6-week** cycle and **MVP-first** scope (no login, no scrapers until post-MVP).

| Phase | Weeks | Focus |
|-------|-------|--------|
| **Scaffold** | 1 | Structure, README, deps (current) |
| **Data layer** | 2 | Schema, DAL CRUD, validation, demo seed data |
| **Analytics** | 3 | Unit normalization, basket inflation %, 4-week demo set |
| **UI** | 4–5 | Entry form, filters in `session_state`, three charts |
| **Polish** | 6 | Performance (&lt;2s load), integrity audit, STEAM demo script |

### Daily loop

1. Activate `.venv`
2. Create a branch for the task (see Git strategy)
3. Implement in **`src/`** first, then **`pages/`**
4. Run `streamlit run app.py` and manually test CRUD + charts
5. Run `pytest` when tests exist
6. Commit with a clear message; open PR or merge to `main` for demo-ready builds

### Layering rule

**UI → processor → DAL → SQLite.** Never import Plotly inside `db_manager.py`; never write SQL in `pages/`.

### Out of scope until post-MVP

- Authentication / multi-user
- CSV/PDF export
- Price alert notifications
- OCR / receipt scanning
- Hosted PostgreSQL (prepare via `.env.example` only)

---

## 8. Git strategy

### Initial repository

```powershell
cd "c:\Users\HpVpro\Desktop\Inflation Tracker"
git init
git add .
git commit -m "chore: initial project scaffold for grocery inflation tracker"
```

### Branch model (simple, STEAM-friendly)

| Branch | Purpose |
|--------|---------|
| `main` | Always demo-runnable; tagged releases for fair submission |
| `feature/*` | One feature per branch (e.g. `feature/dal-crud`, `feature/unit-normalization`) |
| `fix/*` | Bug fixes (e.g. `fix/negative-price-validation`) |

### Commit message convention

```
<type>: <short description>

Types: chore | feat | fix | docs | test | refactor
```

Examples:

- `feat: add price_logs schema and insert helper`
- `fix: reject future dates on entry form`
- `docs: update demo dataset instructions`

### What not to commit

- `.venv/`, `__pycache__/`
- `data/*.db` (local data; regenerate or share a seed script later)
- `.env` with real secrets

### Tags for milestones

```powershell
git tag -a v0.1.0-scaffold -m "Folder structure and docs only"
# Later: v0.2.0-dal, v0.3.0-mvp-demo, v1.0.0-steam
```

### Backup

Push to GitHub/GitLab as a **private** repo if desired; keep no API keys in the tree.

---

## Architecture (reference)

```
Streamlit UI (pages/*, ui_components)
        ↓
Application logic (data_processor)
        ↓
DAL (db_manager)
        ↓
SQLite (data/tracker.db)
```

**Normalization note:** Store `quantity` + `unit_type` on every log; compute comparable `normalized_price` in Pandas before plotting to handle shrinkflation and mixed units (e.g. 1 L vs 500 ml milk).

---

## License / attribution

Add your team name, school, and STEAM fair year before submission.
