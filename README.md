j<div align="center">

<br />

```
  █████╗ ██████╗  ██████╗██╗  ██╗
 ██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝
 ███████║██████╔╝██║      ╚███╔╝ 
 ██╔══██║██╔══██╗██║      ██╔██╗ 
 ██║  ██║██║  ██║╚██████╗██╔╝ ██╗
 ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
```

### The Yield-Bearing Global Currency

*Backed by Gold. Driven by Stocks. Instant as UPI.*

<br />

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-AGPL_v3-blue?style=flat-square)](LICENSE)

<br />

</div>

---

## What is ARCX?

ARCX is a multi-asset, yield-bearing digital currency. It solves a problem every person with savings faces: **your money quietly loses value every year to inflation**.

Traditional savings accounts return 2–3% on a good day. Inflation in India runs at 6–7%. You are going backwards.

ARCX holds your money in a globally diversified vault — 40% global equities, 30% government bonds, 20% gold, 10% cash — and automatically compounds overnight yield back into every token you hold. You transfer it anywhere in the world instantly, with zero fees, via an API that runs as fast as a database query.

> This is not a crypto project. There is no blockchain, no gas fees, no wallet keys to lose. It is a Django backend, a PostgreSQL database, and a React frontend — built to production-grade MNC standards.

<br />

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start — Docker](#quick-start--docker-recommended)
- [Manual Setup](#manual-setup--without-docker)
- [Environment Variables](#environment-variables)
- [Seeding Demo Data](#seeding-demo-data)
- [Running the Test Suite](#running-the-test-suite)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [How It Was Built — Phase by Phase](#how-it-was-built--phase-by-phase)
- [Key Engineering Decisions](#key-engineering-decisions)
- [Roadmap](#roadmap)

<br />

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ARCX System                                 │
│                                                                     │
│   ┌──────────────┐    REST/JWT    ┌─────────────────────────────┐   │
│   │  React + Vite│◄──────────────►│  Django REST Framework      │   │
│   │  (Port 3000) │                │  (Port 8000)                │   │
│   └──────────────┘                └──────────┬──────────────────┘   │
│                                              │                      │
│                          ┌───────────────────┼───────────────────┐  │
│                          │                   │                   │  │
│                   ┌──────▼──────┐   ┌────────▼──────┐            │  │
│                   │  PostgreSQL │   │  Redis Broker │            │  │
│                   │  (Port 5432)│   │  (Port 6379)  │            │  │
│                   └─────────────┘   └───────┬───────┘            │  │
│                                             │                    │  │
│                                    ┌────────▼───────┐            │  │
│                                    │ Celery Worker  │            │  │
│                                    │ + Beat Scheduler│           │  │
│                                    └────────────────┘            │  │
└─────────────────────────────────────────────────────────────────────┘
```

### The Domain Layer (Zero Framework Dependencies)

The financial engine — NAV calculation, Oracle, Circuit Breaker, Dividends — lives in `domain/` with no Django imports. This is intentional. If the API framework changes tomorrow, the math does not.

```
Oracle (3 sources) → TWAP per asset → Median filter
       ↓
ValuationEngine → NAV (USD) → NAV (INR)
       ↓
DividendAccrualEngine → Daily yield per token
       ↓
DriftRebalancer → Trade instructions if drift > 3%
       ↓
CircuitBreakerEngine → Halt conditions (Tier 1 / 2 / 3)
```

<br />

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Backend API** | Django 5.2 + DRF | Battle-tested, excellent ORM, permission classes |
| **Authentication** | SimpleJWT | Stateless tokens, scales horizontally |
| **Database** | PostgreSQL 15 | ACID transactions, NUMERIC type for exact money math |
| **Task Queue** | Celery + Redis | EOD jobs never block the API |
| **Price Oracle** | Yahoo Finance + Alpha Vantage + Twelve Data | 3-source median prevents manipulation |
| **Frontend** | React 18 + Vite | Fast HMR, tree-shaking, modern toolchain |
| **Styling** | Tailwind CSS v3 | Design tokens, consistent spacing |
| **State** | Zustand | Lightweight, no boilerplate |
| **Charts** | Recharts | Composable, React-native |
| **Containerisation** | Docker + Compose | One command to boot everything |
| **CI/CD** | GitHub Actions | Automated tests on every push |

<br />

---

## Prerequisites

Before you begin, ensure you have the following installed on your machine.

**Required**

```
Docker Desktop  ≥ 4.x        https://docker.com/products/docker-desktop
Git             any version   https://git-scm.com
```

**Required for Manual Setup (without Docker)**

```
Python          3.11+         https://python.org
Node.js         18+           https://nodejs.org
PostgreSQL      15+           https://postgresql.org
Redis           7+            https://redis.io
```

**Optional (for live Oracle prices)**

```
Alpha Vantage API key    https://www.alphavantage.co/support/#api-key  (free, 25 req/day)
Twelve Data API key      https://twelvedata.com/register                (free, 800 req/day)
```

The Oracle works with only Yahoo Finance if these keys are absent. Yahoo Finance requires no key.

<br />

---

## Quick Start — Docker (Recommended)

This boots the complete stack — database, cache, API server, background worker, scheduler, and frontend — in under two minutes.

**1. Clone the repository**

```bash
git clone https://github.com/your-username/ARCX_mark-2.git
cd ARCX_mark-2
```

**2. Create your environment file**

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
DJANGO_SECRET_KEY=your-secret-key-here-make-it-long-and-random
DB_PASSWORD=choose_a_strong_password
```

Everything else can stay as the default for local development.

**3. Build and start all services**

```bash
docker compose up --build
```

This will start six containers:

| Container | Role | Port |
|---|---|---|
| `arcx_db` | PostgreSQL database | 5432 |
| `arcx_redis` | Redis broker + cache | 6379 |
| `arcx_backend` | Django API server | 8000 |
| `arcx_worker` | Celery task worker | — |
| `arcx_beat` | Celery scheduler | — |
| `arcx_frontend` | React + Vite dev server | 3000 |

**4. Run database migrations** (first time only)

Open a new terminal while the containers are running:

```bash
docker compose exec backend python manage.py migrate
```

**5. Create a superuser** (for the Admin Panel)

```bash
docker compose exec backend python manage.py createsuperuser
```

**6. Seed demo data** (optional but recommended)

```bash
docker compose exec backend python manage.py seed_simulation
```

This creates 5 test users with 30 days of realistic price history. See [Seeding Demo Data](#seeding-demo-data) for credentials.

**7. Open the app**

```
Frontend Dashboard   →   http://localhost:3000
Django Admin Panel   →   http://localhost:8000/admin
REST API             →   http://localhost:8000/api/v1/
```

<br />

---

## Manual Setup — Without Docker

Use this if you want to develop without containers, or if Docker Desktop is not available.

### Backend

**1. Clone and navigate to the backend**

```bash
git clone https://github.com/your-username/ARCX_mark-2.git
cd ARCX_mark-2/arcx_backend
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

**3. Install Python dependencies**

```bash
pip install -r requirements.txt
```

**4. Create your `.env` file inside `arcx_backend/`**

```bash
cp ../.env.example .env
```

Edit `.env` and set your local PostgreSQL credentials:

```env
DJANGO_SECRET_KEY=any-long-random-string
DEBUG=True
DB_NAME=arcx_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```

**5. Create the PostgreSQL database**

```bash
psql -U postgres -c "CREATE DATABASE arcx_db;"
```

**6. Run migrations**

```bash
python manage.py migrate
```

**7. Create a superuser**

```bash
python manage.py createsuperuser
```

**8. Start the Django development server**

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`.

**9. Start the background scheduler** (separate terminal)

```bash
# Terminal 2 — in arcx_backend/ with .venv active
python manage.py run_scheduler
```

This runs the in-process APScheduler — no Redis required for development. It handles daily NAV snapshots and dividend accrual automatically.

> If you have Redis running and want full Celery instead:
> ```bash
> # Terminal 2 — Celery worker
> celery -A arcx_backend worker -l INFO
>
> # Terminal 3 — Celery beat scheduler
> celery -A arcx_backend beat -l INFO
> ```

### Frontend

**1. Navigate to the frontend directory**

```bash
cd ARCX_mark-2/arcx-frontend
```

**2. Install Node dependencies**

```bash
npm install
```

**3. Create the frontend environment file**

```bash
cp .env.example .env
```

The default points to `http://localhost:8000`, which is correct for manual setup.

**4. Start the Vite development server**

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

<br />

---

## Environment Variables

Full reference for `.env` (root) and `arcx_backend/.env`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | **Yes** | — | Django cryptographic key. Use a 50+ character random string. |
| `DEBUG` | No | `False` | Set `True` for local development only. Never in production. |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated list of valid hostnames. |
| `DB_NAME` | No | `arcx_db` | PostgreSQL database name. |
| `DB_USER` | No | `arcx_user` | PostgreSQL username. |
| `DB_PASSWORD` | **Yes** | — | PostgreSQL password. |
| `DB_HOST` | No | `db` (Docker) / `localhost` | Database host. Use `db` inside Docker, `localhost` outside. |
| `DB_PORT` | No | `5432` | PostgreSQL port. |
| `REDIS_URL` | No | `redis://redis:6379/0` | Redis connection string. |
| `ALPHA_VANTAGE_KEY` | No | — | Optional. Adds a second Oracle price source. |
| `TWELVE_DATA_KEY` | No | — | Optional. Adds a third Oracle price source. |
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | Where the React app sends API requests. |

<br />

---

## Seeding Demo Data

The simulation seed engine creates a fully populated environment for testing and demonstration.

```bash
# With Docker
docker compose exec backend python manage.py seed_simulation

# Without Docker (in arcx_backend/ with venv active)
python manage.py seed_simulation

# Reset and re-seed from scratch
python manage.py seed_simulation --flush
```

**What gets created:**

- 30 days of realistic NAV price history using Geometric Brownian Motion
- 5 test users with approved KYC and active wallets
- Historical deposits, P2P transfers, and dividend accruals spread across the timeline
- VaultSnapshot and NAVHistory records populating the price chart

**Test user credentials:**

| Name | Email | Password |
|---|---|---|
| Alice Sharma | `alice@arcxtest.com` | `Test@12345` |
| Bob Mehta | `bob@arcxtest.com` | `Test@12345` |
| Charlie Rao | `charlie@arcxtest.com` | `Test@12345` |
| Diana Patel | `diana@arcxtest.com` | `Test@12345` |
| Eve Krishnan | `eve@arcxtest.com` | `Test@12345` |

**Backfilling real historical data** (requires internet):

```bash
# Replace GBM simulation with actual SPY, TLT, GLD market data
python manage.py backfill_nav --days 60

# Overwrite existing history
python manage.py backfill_nav --days 90 --overwrite
```

<br />

---

## Running the Test Suite

**With Docker**

```bash
docker compose exec backend python manage.py test
```

**Without Docker**

```bash
cd arcx_backend
python manage.py test

# Run specific test modules
python manage.py test tests.test_auth
python manage.py test tests.test_phase5
python manage.py test tests.test_observability

# Run Phase 1 pure Python tests (no Django required)
cd ..
python -m pytest tests/test_phase1b.py -v
```

**What the test suite covers:**

| Module | Coverage |
|---|---|
| `test_auth.py` | Registration, JWT, KYC submission, full onboarding flow |
| `test_phase5.py` | Circuit Breaker all tiers, TVL spike, EOD Celery tasks |
| `test_observability.py` | Structured logger output, `@log_operation` decorator |
| `test_phase1b.py` | Dividend math, drift rebalancer, Oracle TWAP |

**Reading logs after running tests:**

```bash
python manage.py read_logs --summary
python manage.py read_logs --event DEPOSIT_COMPLETED
python manage.py read_logs --level ERROR
python manage.py read_logs --event TRANSFER_COMPLETED --tail 20
```

<br />

---

## API Reference

Base URL: `http://localhost:8000/api/v1/`

All authenticated endpoints require the header:
```
Authorization: Bearer <access_token>
```

Financial mutation endpoints (deposit, withdraw, transfer) additionally require:
```
Idempotency-Key: <uuid-v4>
```

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Create account. Returns JWT pair immediately. |
| `POST` | `/api/auth/token/` | Public | Login. Returns `access` + `refresh` tokens. |
| `POST` | `/api/auth/token/refresh/` | Public | Refresh expired access token. |
| `GET` | `/auth/me` | Required | Full user profile with wallet balance. |
| `POST` | `/auth/logout` | Required | Blacklist refresh token. |

### KYC

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/kyc/submit` | Required | Submit KYC document reference. Auto-approves in demo mode. |
| `GET` | `/kyc/status` | Required | Current KYC tier, daily limit, submission history. |

### Wallet

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/wallet/` | Required | Balance + unrealized P&L. |
| `POST` | `/wallet/deposit` | KYC Approved | Convert INR → ARCX. Requires `Idempotency-Key`. |
| `POST` | `/wallet/withdraw` | KYC Approved | Convert ARCX → INR. 0.1% instant liquidity fee, capped at $100. |
| `GET` | `/wallet/history` | Required | Paginated transaction history. `?limit=20` |

### Transfers

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/transfer/` | KYC Approved | Zero-fee P2P ARCX transfer. Atomic DB update. Requires `Idempotency-Key`. |

### Oracle & NAV

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/oracle/price` | Public | Live TWAP prices (SPY, TLT, GLD, USD/INR) + current NAV. |
| `GET` | `/nav/history` | Public | Historical NAV series. `?days=30` (max 365). |
| `GET` | `/nav/today` | Public | Today's published NAV with SHA256 audit hash. |

### Portfolio

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/portfolio/analytics` | Required | Holdings, P&L series, yield earned, transaction breakdown. |

### Admin (Superuser Only)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/users` | Superuser | All users with wallet balances. |
| `GET` | `/admin/kyc` | Superuser | Pending KYC submissions queue. |
| `POST` | `/admin/kyc` | Superuser | Approve or reject a KYC record. |
| `POST` | `/admin/nav/compute` | Superuser | Manually trigger EOD NAV pipeline. |

### Example: Register and Deposit

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "secure123", "full_name": "Your Name"}'

# Response includes access_token — use it below

# 2. Submit KYC
curl -X POST http://localhost:8000/api/v1/kyc/submit \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"tier": "tier_1", "document_type": "aadhaar", "document_ref": "DEMO_REF_001"}'

# 3. Deposit INR
curl -X POST http://localhost:8000/api/v1/wallet/deposit \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(python -c 'import uuid; print(uuid.uuid4())')" \
  -d '{"amount_inr": "5000.00"}'
```

<br />

---

## Project Structure

```
ARCX_mark-2/
│
├── .env.example                        # Environment variable template
├── .github/
│   └── workflows/
│       └── test.yml                    # GitHub Actions CI pipeline
├── docker-compose.yml                  # Full stack container orchestration
├── requirements.txt                    # Python dependencies
├── pytest.ini                          # Test runner configuration
│
├── arcx_backend/                       # Django Backend
│   ├── manage.py
│   │
│   ├── arcx_backend/                   # Django project config
│   │   ├── settings.py                 # DB, JWT, Celery, CORS, Logging
│   │   ├── urls.py                     # Global URL routing
│   │   ├── celery.py                   # Celery application + beat schedule
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── domain/                         # ★ Financial Engine (no Django imports)
│   │   ├── oracle.py                   # Multi-source TWAP Oracle
│   │   ├── valuation.py                # NAV calculation engine
│   │   ├── dividend.py                 # Daily yield accrual
│   │   ├── rebalancer.py               # Drift detection + trade instructions
│   │   ├── circuit_breaker.py          # 3-tier market halt system
│   │   └── nav_report.py               # SHA256-signed daily NAV report
│   │
│   ├── arcx_core/                      # Django Application
│   │   ├── models.py                   # User, Wallet, Transaction, KYCRecord,
│   │   │                               # VaultSnapshot, NAVHistory, CircuitBreakerLog
│   │   ├── serializers.py              # Request/response schemas
│   │   ├── serializers_auth.py         # Auth-specific schemas
│   │   ├── permissions.py              # IsKYCApproved, IsWalletActive, IsCircuitBreakerClear
│   │   ├── exceptions.py               # Normalised error shapes
│   │   ├── middleware.py               # Idempotency + Request logging
│   │   ├── logger.py                   # Typed structured logger
│   │   ├── auth_backend.py             # Email-based JWT authentication
│   │   ├── apps.py
│   │   ├── urls.py                     # v1 API route map
│   │   │
│   │   ├── views/
│   │   │   ├── auth_views.py           # Register, Me, Logout
│   │   │   ├── wallet_views.py         # Balance, Deposit, Withdraw, History
│   │   │   ├── transfer_views.py       # P2P Transfer
│   │   │   ├── oracle_views.py         # Live price, NAV history, Today NAV
│   │   │   ├── kyc_views.py            # Submit, Status
│   │   │   ├── portfolio_views.py      # Analytics, P&L series
│   │   │   └── admin_views.py          # User list, KYC approval, NAV trigger
│   │   │
│   │   ├── services/
│   │   │   ├── wallet_service.py       # Deposit/withdraw business logic
│   │   │   ├── transfer_service.py     # P2P transfer with deadlock prevention
│   │   │   ├── auth_service.py         # Registration (atomic user + wallet)
│   │   │   └── kyc_service.py          # KYC submission + tier management
│   │   │
│   │   ├── tasks/
│   │   │   ├── eod_tasks.py            # take_vault_snapshot, publish_daily_nav,
│   │   │   │                           # accrue_daily_dividends, run_rebalancing_check
│   │   │   └── monitoring_tasks.py     # check_circuit_breaker (every 2 min)
│   │   │
│   │   ├── management/commands/
│   │   │   ├── seed_simulation.py      # 30-day GBM simulation + test users
│   │   │   ├── backfill_nav.py         # Real yfinance historical data
│   │   │   ├── run_scheduler.py        # In-process APScheduler (no Redis needed)
│   │   │   └── read_logs.py            # CLI structured log viewer
│   │   │
│   │   └── migrations/
│   │
│   └── tests/
│       ├── test_auth.py                # Full onboarding lifecycle
│       ├── test_phase5.py              # Circuit Breaker + EOD tasks
│       └── test_observability.py       # Structured logger output
│
├── tests/
│   └── test_phase1b.py                 # Pure Python domain tests
│
└── arcx-frontend/                      # React Frontend
    ├── Dockerfile
    ├── vite.config.js
    ├── tailwind.config.js
    │
    └── src/
        ├── App.jsx                     # Router + auth guard
        ├── index.css                   # Glassmorphism design system
        │
        ├── api/
        │   ├── client.js               # Axios + JWT interceptor + silent refresh
        │   ├── auth.js
        │   ├── wallet.js
        │   ├── oracle.js
        │   ├── kyc.js
        │   ├── portfolio.js
        │   └── admin.js
        │
        ├── store/
        │   ├── authStore.js            # Zustand auth state
        │   └── useStore.js             # Wallet, oracle, KYC state
        │
        ├── pages/
        │   ├── AuthPage.jsx            # Login + Register with onboarding carousel
        │   ├── DashboardPage.jsx       # Apple Stocks-style NAV chart + vault allocation
        │   ├── WalletPage.jsx          # Deposit / Withdraw / Transfer + history
        │   ├── PortfolioPage.jsx       # P&L chart, yield breakdown, analytics
        │   ├── KYCPage.jsx             # Multi-step verification wizard
        │   ├── ProfilePage.jsx         # Settings, security, bank accounts
        │   └── AdminPage.jsx           # Treasury ops (superuser only)
        │
        └── components/
            ├── layout/                 # AppLayout, Navbar, AdminRoute
            ├── ui/                     # NavTicker (live price widget)
            ├── dashboard/              # StatCard, NAVChart, VaultAllocation, CircuitBreakerBanner
            ├── wallet/                 # DepositForm, WithdrawForm, TransactionTable
            └── kyc/                    # KYCWizard, KYCStatusCard
```

<br />

---

## How It Was Built — Phase by Phase

ARCX was developed in structured phases, each adding a distinct production-grade capability.

### Phase 0 — Design
Whitepaper, product requirements document, circuit breaker specification, and database schema designed before a single line of code was written.

### Phase 1 — Core Financial Engine
Pure Python. Zero framework dependencies.
- Multi-source Oracle: Yahoo Finance + Alpha Vantage + Twelve Data. TWAP per source, median across sources — prevents flash crash manipulation.
- ValuationEngine: NAV = Total Vault Value (USD) / ARCX Supply.
- DividendAccrualEngine: Daily yield across 4 asset classes (1.3% stocks, 4% bonds, 0% gold, 5% cash). 85% to users, 15% retained as treasury liquidity buffer.
- DriftRebalancer: Detects ± 3% deviation from 40/30/20/10 target, generates trade instructions.
- NAVReportGenerator: SHA256-signed JSON reports for tamper-proof audit trail.

### Phase 2 — Database Schema
PostgreSQL with non-negotiable enterprise standards: UUID primary keys, `created_at`/`updated_at` on every table, soft deletes via `deleted_at`, `Decimal` fields for all monetary values.

### Phase 3 — Django REST API
Versioned endpoints under `/api/v1/`. Idempotency middleware prevents double-spend on network retries. Stateless JWT authentication.

### Phase 4 — Observability
Typed structured logger (`arcx_logger`). Every financial event emits a JSON log entry with `event`, `user_id`, `tx_id`, `duration_ms`. `read_logs` management command provides CLI-level analytics without Datadog.

### Phase 5 — Circuit Breaker + Celery
Three-tier circuit breaker mirroring SEBI and NYSE halt rules. Celery Beat schedule for autonomous EOD pipeline: snapshot at 15:30 IST, rebalancing at 15:45, dividend accrual at 00:01, NAV publish at 16:00.

### Phase 6 — Auth, KYC, Registration
Atomic registration (Django auth user + ARCX user + Wallet in one transaction). KYC tier system with daily transaction limits. Token blacklist on logout.

### Phase 7 — CORS + Security
Django CORS headers. Environment-based secret management. Input validation via DRF serializers.

### Phase 8 — Frontend + Docker + CI
React 18 + Vite + Tailwind. Apple-inspired glassmorphism UI. Full Docker Compose stack. GitHub Actions CI pipeline with PostgreSQL and Redis service containers.

### Phase 9 — Simulation Seed Engine
Geometric Brownian Motion price simulation (μ = 0.08%/day, σ = 0.35%/day). 5 deterministic test users with realistic deposit schedules, P2P transfers, and dividend histories across 30 days.

### Phase 10 — Portfolio Analytics + Admin Panel
User-facing P&L series, yield breakdown, and transaction analytics. Superuser treasury panel with user monitoring, KYC approval queue, and manual NAV trigger.

<br />

---

## Key Engineering Decisions

**Why not blockchain?**

Blockchain adds latency, gas fees, key management complexity, and regulatory ambiguity — none of which serve the user. A transfer in ARCX is two `UPDATE` statements inside a `transaction.atomic()` block. It settles in under 100ms with zero fees. Blockchain cannot compete with that for this use case.

**Why TWAP over spot price?**

A single spot price can be moved by one large trade. TWAP (Time-Weighted Average Price) over 5 days of hourly closes makes manipulation prohibitively expensive — the attacker would need to sustain an artificial price for days, not seconds.

**Why median across three Oracle sources?**

Mean is sensitive to outliers. If one source returns a corrupted value (e.g., 9999 instead of 530), the mean breaks. The median ignores it automatically. This is standard practice in institutional and DeFi price feeds.

**Why `select_for_update()` on every wallet write?**

Without a row-level lock, two concurrent deposits can both read `balance = 100`, both add `50`, and both write `150`. The correct answer is `200`. `SELECT FOR UPDATE` in PostgreSQL forces the second transaction to wait until the first commits, eliminating this race condition entirely.

**Why idempotency keys on financial mutations?**

Mobile networks drop connections. Users double-tap buttons. Without idempotency, a retry creates a second transaction. With it, the middleware hashes the request body, caches the response, and returns the same response on any retry — the database is only written once.

**Why `Decimal` instead of `float` for money?**

`float(0.1) + float(0.2)` returns `0.30000000000000004` in Python. For a ₹10,00,000 transaction this is a meaningful rounding error. PostgreSQL's `NUMERIC` type and Python's `Decimal` are exact. Financial software must never use floating point for monetary values.

<br />

---

## Roadmap

- [ ] DigiLocker / NSDL integration for real KYC verification
- [ ] Broker API integration for actual asset rebalancing execution
- [ ] WebSocket live price push (replace 30-second polling)
- [ ] IPFS storage for daily NAV reports (full decentralisation of audit trail)
- [ ] Mobile app (React Native, shared API)
- [ ] RBI regulatory compliance review
- [ ] Multi-currency vault support (USD, EUR denominated tokens)

<br />

---

## License

AGPL-3.0 License — see [LICENSE](LICENSE) for details.

<br />

---

<div align="center">
Built with precision.
Every design decision in this codebase has a reason.
<br />
Designed by Dhruv
</div>
