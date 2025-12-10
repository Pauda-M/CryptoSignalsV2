# CryptoTrader Unification: Visual Reference Guide

## Directory Structure Comparison

### BEFORE (Current State - Two Separate Projects)

```
crypto-signals/
│
├── 📦 ROOT LEVEL
│   ├── package.json (PM2 only)
│   ├── ecosystem.config.js (main project PM2)
│   ├── python-ml-pm2-ecosystem.config.js (ML project PM2)
│   ├── .env
│   ├── install.bat
│   └── .git/
│
├── 🖥️  MAIN PROJECT (crypto-signals)
│   ├── backend-engine/              [Express API + PostgreSQL]
│   │   ├── src/
│   │   │   ├── server.js
│   │   │   ├── db.js
│   │   │   ├── bootstrap.js
│   │   │   ├── routes/
│   │   │   │   ├── signals.js
│   │   │   │   ├── meme.js
│   │   │   │   ├── pumpx.js
│   │   │   │   ├── timeframes.js
│   │   │   │   ├── quant.js
│   │   │   │   ├── portfolios.js
│   │   │   │   └── mlRoutes.js
│   │   │   ├── services/
│   │   │   └── utils/
│   │   ├── package.json (Express, pg, cors, socket.io)
│   │   ├── Dockerfile
│   │   ├── start-backend.cmd
│   │   └── start-backend.ps1
│   │
│   ├── frontend-engine/             [React + Vite SPA]
│   │   ├── src/
│   │   │   ├── App.jsx
│   │   │   ├── main.jsx
│   │   │   ├── styles.css
│   │   │   ├── tabs/
│   │   │   │   ├── SignalsTab.jsx
│   │   │   │   ├── MemeTab.jsx
│   │   │   │   ├── PumpxRadarTab.jsx
│   │   │   │   ├── PumpxMLTab.jsx
│   │   │   │   ├── PumpxAlertsTab.jsx
│   │   │   │   ├── PumpxTrendsTab.jsx
│   │   │   │   └── PumpxHourlychartTab.jsx
│   │   │   ├── components/
│   │   │   ├── services/
│   │   │   │   ├── api.js
│   │   │   │   └── pumpxApi.js
│   │   │   └── utils/
│   │   ├── package.json (React, Vite, Tailwind, Recharts)
│   │   ├── vite.config.js
│   │   ├── tailwind.config.js
│   │   ├── start-frontend.ps1
│   │   └── Dockerfile
│   │
│   ├── signal-engine/               [TypeScript Signal Generator]
│   │   ├── src-ts/
│   │   │   ├── engine.ts
│   │   │   └── types.ts
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── Dockerfile
│   │
│   ├── quant-engine/                [Node.js Metrics Calculator]
│   │   ├── src/
│   │   │   ├── quantEngine.js
│   │   │   ├── db.js
│   │   │   ├── math.js
│   │   │   └── ohlcFetcher.js
│   │   └── package.json
│   │
│   ├── pumpx-streamer-engine/       [Socket.IO Real-time Streamer]
│   │   ├── src/
│   │   │   ├── server.js
│   │   │   ├── wssStreamer.js
│   │   │   └── alerts.js
│   │   └── package.json
│   │
│   ├── ml/                          [Python ML Pipeline (PumpX)]
│   │   ├── src/ (implied)
│   │   ├── .venv-ml/                [Python virtual env]
│   │   ├── data_ingestion/
│   │   │   ├── ingest_pumpfun_live.py
│   │   │   └── ingest_pumpx_scoring.py
│   │   ├── train_pumpx_xgb.py
│   │   ├── train_transformer_v2.py
│   │   ├── pumpx_predictor.py
│   │   ├── export_training_data.py
│   │   └── requirements.txt
│   │
│   └── db/
│       ├── db.js
│       └── schema.sql
│
├── 📦 LEGACY PROJECT (xrp-btc-spread) ← NESTED INSIDE
│   │  [SEPARATE, PARALLEL SYSTEM]
│   ├── backend-engine/              [Python Backend - SEPARATE]
│   │   ├── services/
│   │   ├── requirements.txt
│   │   ├── run_backend.bat
│   │   └── run_backend.py
│   │
│   ├── frontend-engine/             [React - DUPLICATE]
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── services/
│   │   │   └── styles/
│   │   ├── node_modules/             [SEPARATE]
│   │   ├── package.json              [SEPARATE]
│   │   ├── package-lock.json
│   │   ├── vite.config.js
│   │   └── run_frontend.bat
│   │
│   ├── ml-engine/                   [Python ML - SEPARATE/DUPLICATE]
│   │   ├── feature_builder_v2.py
│   │   ├── train_xgb_pg.py
│   │   ├── train_transformer_v2.py
│   │   ├── models/
│   │   ├── venv/                     [SEPARATE Python env]
│   │   ├── requirements.txt          [SEPARATE]
│   │   ├── run_ml.bat
│   │   └── run_ml.py
│   │
│   ├── package.json
│   ├── .env
│   ├── README_ml_v2.txt
│   └── [Other config files]
│
└── 📁 OTHER DIRECTORIES
    ├── pm2-launchers/
    ├── GIT/
    ├── logs/
    ├── temp/
    └── ZIP/
```

### AFTER (Proposed Unified State)

```
crypto-signals/
│
├── 📦 UNIFIED ROOT
│   ├── package.json                 ← SINGLE (all services)
│   ├── ecosystem.config.js          ← SINGLE (all PM2 configs merged)
│   ├── docker-compose.yml           ← NEW (unified deployment)
│   ├── .env                         ← SINGLE (all configs)
│   ├── .env.example                 ← NEW (template)
│   ├── install.bat
│   └── .git/
│
├── 🏗️  SERVICES DIRECTORY (NEW ORGANIZATION)
│   ├── backend/                     ← RENAMED (was backend-engine)
│   │   ├── src/
│   │   │   ├── server.js
│   │   │   ├── db.js
│   │   │   ├── bootstrap.js
│   │   │   ├── routes/
│   │   │   │   ├── signals.js       (existing)
│   │   │   │   ├── meme.js          (existing)
│   │   │   │   ├── pumpx.js         (existing)
│   │   │   │   ├── xrpBtc.js        ← NEW (MIGRATED)
│   │   │   │   ├── timeframes.js
│   │   │   │   ├── quant.js
│   │   │   │   ├── portfolios.js
│   │   │   │   └── ml.js
│   │   │   ├── services/
│   │   │   │   ├── signalService.js
│   │   │   │   ├── pumpxService.js
│   │   │   │   └── xrpBtcService.js ← NEW (MIGRATED)
│   │   │   └── utils/
│   │   ├── package.json             ← UPDATED (merged deps)
│   │   └── Dockerfile
│   │
│   ├── frontend/                    ← RENAMED (was frontend-engine)
│   │   ├── src/
│   │   │   ├── App.jsx              ← UPDATED (XrpBtcTab added)
│   │   │   ├── main.jsx
│   │   │   ├── styles.css           ← MERGED (both stylesheets)
│   │   │   ├── tabs/
│   │   │   │   ├── SignalsTab.jsx
│   │   │   │   ├── MemeTab.jsx
│   │   │   │   ├── PumpxRadarTab.jsx
│   │   │   │   ├── PumpxMLTab.jsx
│   │   │   │   ├── PumpxAlertsTab.jsx
│   │   │   │   ├── PumpxTrendsTab.jsx
│   │   │   │   ├── PumpxHourlychartTab.jsx
│   │   │   │   └── XrpBtcTab.jsx    ← NEW (MIGRATED)
│   │   │   ├── components/
│   │   │   │   ├── shared/          (common)
│   │   │   │   ├── pumpx/           (existing)
│   │   │   │   └── xrpbtc/          ← NEW (MIGRATED)
│   │   │   ├── services/
│   │   │   │   ├── api.js
│   │   │   │   ├── pumpxApi.js
│   │   │   │   └── xrpBtcApi.js     ← NEW (MIGRATED)
│   │   │   ├── hooks/
│   │   │   └── utils/
│   │   ├── package.json             ← UPDATED (merged deps)
│   │   ├── vite.config.js           ← MERGED
│   │   ├── tailwind.config.js       ← MERGED
│   │   └── Dockerfile
│   │
│   ├── signal-engine/               (unchanged)
│   │   ├── src-ts/
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── quant-engine/                (unchanged)
│   │   ├── src/
│   │   └── package.json
│   │
│   ├── pumpx-streamer-engine/       (unchanged)
│   │   ├── src/
│   │   └── package.json
│   │
│   └── ml-engine/                   ← UNIFIED ML
│       ├── src/
│       │   ├── orchestrator.py      ← NEW (unified entry point)
│       │   ├── pipelines/
│       │   │   ├── pumpx/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── train.py
│       │   │   │   ├── features.py
│       │   │   │   └── ingest.py
│       │   │   └── xrp_btc/         ← NEW (MIGRATED)
│       │   │       ├── __init__.py
│       │   │       ├── train.py     ← FROM xrp-btc-spread
│       │   │       ├── features.py  ← FROM xrp-btc-spread
│       │   │       └── ingest.py
│       │   ├── models/
│       │   │   ├── xgb.py           (shared base)
│       │   │   ├── transformer.py   (shared base)
│       │   │   ├── xgb_pumpx.py
│       │   │   ├── xgb_xrp_btc.py   ← NEW
│       │   │   ├── transformer_pumpx.py
│       │   │   └── transformer_xrp_btc.py ← NEW
│       │   ├── features/
│       │   │   ├── pumpx_features.py
│       │   │   └── xrp_btc_features.py ← NEW (MIGRATED)
│       │   ├── utils/
│       │   │   ├── db.py
│       │   │   └── logger.py
│       │   └── data/
│       │       ├── pumpx/
│       │       └── xrp_btc/         ← NEW
│       ├── models/                  ← Shared model storage
│       │   ├── pumpx/
│       │   │   ├── xgb_latest.pkl
│       │   │   └── transformer_latest.pt
│       │   └── xrp_btc/             ← NEW
│       │       ├── xgb_latest.pkl
│       │       └── transformer_latest.pt
│       ├── .venv/                   ← UNIFIED Python (merged .venv-ml/ + venv/)
│       ├── requirements.txt         ← MERGED
│       ├── run_ml.sh                ← NEW (unified entry)
│       └── Dockerfile
│
├── 🔧 SHARED DIRECTORY (NEW)
│   ├── types/
│   │   ├── signals.ts
│   │   ├── tokens.ts
│   │   └── xrpbtc.ts               ← NEW
│   ├── schemas/
│   │   ├── signals.sql
│   │   ├── tokens.sql
│   │   └── xrpbtc.sql              ← NEW
│   ├── utils/
│   │   ├── logger.js
│   │   ├── validators.js
│   │   └── db-helpers.js
│   └── config/
│       ├── database.js
│       └── constants.js
│
├── 📚 DOCS DIRECTORY (NEW/UPDATED)
│   ├── ARCHITECTURE.md              ← NEW
│   ├── API.md                       ← UPDATED (added xrp-btc endpoints)
│   ├── DB_SCHEMA.md                 ← NEW
│   ├── DEPLOYMENT.md                ← NEW
│   ├── DEVELOPMENT.md               ← NEW
│   ├── MIGRATION.md                 ← From migration docs
│   └── UNIFICATION_SUMMARY.md       ← This project's docs
│
├── ⚙️  OPS DIRECTORY (NEW)
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   ├── frontend.Dockerfile
│   │   ├── ml-engine.Dockerfile
│   │   └── .dockerignore
│   ├── k8s/                         (optional)
│   │   ├── backend-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   └── postgres-statefulset.yaml
│   ├── scripts/
│   │   ├── setup-unified-env.sh     ← NEW
│   │   ├── migrate-xrpbtc-data.sql  ← NEW
│   │   ├── backup-db.sh             ← NEW
│   │   └── test-all-services.sh     ← NEW
│   └── monitoring/
│       └── prometheus.yml            (optional)
│
├── 📁 LEGACY (Archive)
│   └── xrp-btc-spread-backup/       ← ARCHIVE ONLY
│       ├── backend-engine/
│       ├── frontend-engine/
│       ├── ml-engine/
│       └── README.md (for reference)
│
└── 📁 OTHER
    ├── pm2-launchers/               (can be archived)
    ├── logs/
    ├── temp/
    └── GIT/
```

---

## API Endpoint Mapping

### BEFORE (Two Separate Systems)

```
MAIN PROJECT (crypto-signals):
GET    /api/signals          ← Core signals
GET    /api/meme             ← Meme tokens
GET    /api/pumpx/*          ← PumpX data
GET    /api/quant/*          ← Portfolio metrics
GET    /api/timeframes/*     ← Timeframe data
POST   /api/ml/build         ← ML training
POST   /api/ml/train
POST   /api/ml/deploy

LEGACY PROJECT (xrp-btc-spread):
GET    /backend/metrics      ← XRP-BTC metrics
POST   /backend/train        ← XRP-BTC training
[NO UNIFIED API - Separate Python backend]
```

### AFTER (Unified System)

```
UNIFIED API (Single Express Server):
─────────────────────────────────────
SIGNALS ENDPOINTS:
GET    /api/signals          ← Core signals
GET    /api/signals/:id      ← Signal details

MEME ENDPOINTS:
GET    /api/meme             ← Meme tokens
GET    /api/meme/:id         ← Token details

PUMPX ENDPOINTS:
GET    /api/pumpx/radar      ← Live radar
GET    /api/pumpx/alerts     ← Active alerts
GET    /api/pumpx/trends     ← Trend analysis
GET    /api/pumpx/hourly/:mint

XRP-BTC ENDPOINTS (NEW):        ← MIGRATED
GET    /api/xrp-btc/metrics   ← XRP-BTC metrics
GET    /api/xrp-btc/alerts    ← XRP-BTC alerts
GET    /api/xrp-btc/history   ← Historical data

PORTFOLIO ENDPOINTS:
GET    /api/portfolios        ← User portfolios
POST   /api/portfolios        ← Create portfolio
PUT    /api/portfolios/:id    ← Update portfolio

QUANT ENDPOINTS:
GET    /api/quant/metrics/:portfolio_id

ML ENDPOINTS:
POST   /api/ml/train          ← Train model
  Body: { project: 'pumpx|xrp-btc', model: 'xgb|transformer' }
GET    /api/ml/status         ← Training status
GET    /api/ml/models         ← Available models

TIMEFRAME ENDPOINTS:
GET    /api/timeframes        ← Available timeframes

HEALTH:
GET    /api/health            ← API health check
```

---

## Database Schema Evolution

### BEFORE (Possible Separate DBs)

```
crypto_signals_db:
├── meme_tokens
├── meme_signals
├── meme_alpha_signals
├── pumpx_live
├── pumpx_radar
├── portfolio_holders
├── portfolios
├── portfolio_positions
└── [timeframes, users, settings]

xrp_btc_spread_db:  ← SEPARATE OR DIFFERENT SCHEMA
├── xrp_metrics
├── btc_metrics
├── xrp_btc_alerts
├── predictions
└── [model_versions]
```

### AFTER (Single Unified DB)

```
crypto_signals_unified:
│
├── Core Tables:
│   ├── tokens                ← ALL token types
│   │   ├── id
│   │   ├── symbol, name
│   │   ├── type (ENUM: meme, pumpx, xrp, btc, other)
│   │   ├── source (pumpfun, binance, etc)
│   │   └── metadata (JSON)
│   │
│   └── signals               ← ALL signal types
│       ├── id
│       ├── token_id
│       ├── signal_type
│       ├── signal_source (core, alpha, pumpx, xrp_btc)
│       ├── value, confidence
│       └── timestamp
│
├── PumpX Tables:
│   ├── pumpx_live_data
│   ├── pumpx_alerts
│   ├── pumpx_radar_state
│   └── pumpx_trends
│
├── XRP-BTC Tables (NEW):     ← MIGRATED
│   ├── xrp_btc_metrics
│   ├── xrp_btc_alerts
│   ├── xrp_btc_predictions
│   └── xrp_btc_historical
│
├── Portfolio Tables:
│   ├── portfolios
│   ├── portfolio_positions
│   ├── portfolio_metrics
│   └── portfolio_alerts
│
├── ML Tables:
│   ├── ml_models
│   │   ├── id, name, type
│   │   ├── target_project (pumpx, xrp_btc)
│   │   ├── accuracy, created_at
│   │   └── model_path
│   ├── training_history
│   ├── model_versions
│   └── feature_store
│
└── Admin Tables:
    ├── users
    ├── settings
    ├── audit_log
    └── timeframes
```

---

## Service Communication Diagram

### BEFORE (Loose Coupling, Some Redundancy)

```
┌─────────────────┐
│   Frontend      │
│   (React SPA)   │
└────────┬────────┘
         │ HTTP /:5173
         │
         ├─────────────────────────────────────────────┐
         │                                             │
         ▼                                             ▼
    ┌─────────────┐                          ┌──────────────────┐
    │  Backend    │                          │  Python Backend  │
    │  (Port 4000)│                          │  (Separate)      │
    │  Express    │                          │  NOT INTEGRATED  │
    └─────────────┘                          └──────────────────┘
         │ │ │                                       │
         │ │ │ (Different DBs or schemas)            │
         │ │ │                                       │
         ▼ ▼ ▼                                       ▼
    ┌──────────────────┐                  ┌──────────────────┐
    │   PostgreSQL     │                  │   PostgreSQL     │
    │   (crypto_       │                  │   (xrp_btc_      │
    │   signals)       │                  │   spread)        │
    └──────────────────┘                  └──────────────────┘
         ▲ ▲ ▲                                  ▲
         │ │ │ │                                │
    ┌────┘ │ └──────────────┬──────────────────┘
    │      │                │
    │  Signal Engine    Quant Engine      ML Pipeline
    │  (TypeScript)     (Node.js)         (Python)
    │                                     [SEPARATE VENV]
    │
    └─ NO CROSS-SYSTEM DATA SHARING
```

### AFTER (Tight Integration, Shared Resources)

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED FRONTEND (React)                     │
│  Tabs: Signals | Meme | PumpX | XRP-BTC | ML | Settings         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              UNIFIED BACKEND (Express - Port 4000)               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Routes:                                                 │    │
│  │  • /api/signals          (signals-routes)               │    │
│  │  • /api/meme             (meme-routes)                  │    │
│  │  • /api/pumpx/*          (pumpx-routes)                 │    │
│  │  • /api/xrp-btc/*        (xrpbtc-routes) NEW            │    │
│  │  • /api/portfolios       (portfolio-routes)             │    │
│  │  • /api/quant/*          (quant-routes)                 │    │
│  │  • /api/ml/*             (ml-routes)                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────┬────────────────────────────────────────┬────────────┘
             │                                        │
             ▼                                        ▼
    ┌────────────────────────────┐         ┌──────────────────────┐
    │   SHARED PostgreSQL        │         │  WebSocket/Socket.IO │
    │   (Single Instance)        │         │  (Streaming Data)    │
    │                            │         │                      │
    │ • All tokens              │         │ pumpx-streamer-     │
    │ • All signals             │         │ engine (Port 4101)  │
    │ • XRP-BTC data            │         │                      │
    │ • Metrics & alerts        │         └──────────────────────┘
    │ • ML models & history     │
    └────────────────────────────┘
             ▲ ▲ ▲
             │ │ │
    ┌────────┘ │ └───────────────┬──────────────┐
    │          │                 │              │
    ▼          ▼                 ▼              ▼
┌────────┐ ┌────────┐ ┌──────────────┐ ┌──────────────────┐
│Signal  │ │Quant   │ │ML Orchestr.  │ │Historical Data   │
│Engine  │ │Engine  │ │(Python)      │ │Ingestion         │
│(TS)    │ │(Node)  │ │              │ │(Python)          │
└────────┘ └────────┘ │ • Pumpx      │ │ (Shared .venv/)  │
                      │ • XRP-BTC    │ │                  │
                      │   (NEW)      │ └──────────────────┘
                      └──────────────┘

ALL SERVICES MANAGED BY: pm2 (SINGLE ECOSYSTEM.CONFIG.JS)
ALL CONFIGURED BY:      .env (SINGLE FILE)
ALL DEPLOYED WITH:      docker-compose.yml (SINGLE FILE)
```

---

## Component Interaction Flow

### Data Flow: XRP-BTC Metrics Visualization

```
BEFORE (Two Systems):
User Views XRP-BTC Dashboard
    ↓
[SEPARATE] Python Backend /metrics
    ↓
[SEPARATE] xrp_btc_spread_db
    ↓
[SEPARATE] React Frontend Component
    ↓
Display to User
[NO INTEGRATION WITH MAIN PLATFORM]

AFTER (Unified System):
User Clicks "XRP-BTC" Tab
    ↓
XrpBtcTab.jsx Component
    ↓
xrpBtcApi.js.getXrpBtcMetrics()
    ↓
GET /api/xrp-btc/metrics (Express Backend)
    ↓
xrpBtcRoutes.js → xrpBtcService.js
    ↓
Query: SELECT * FROM xrp_btc_metrics
    ↓
[SHARED] PostgreSQL Instance
    ↓
Return JSON Response
    ↓
XrpBtcTab.jsx Renders Charts
    ↓
Display alongside Signals/Meme/PumpX data
[FULLY INTEGRATED]
```

### Training Flow: ML Pipeline

```
BEFORE:
User Clicks "Train" Button (XRP-BTC)
    ↓
Runs: run_ml.bat (Python script)
    ↓
Uses: xrp-btc-spread/ml-engine/venv/
    ↓
Trains separate model
    ↓
Saves to: xrp-btc-spread/ml-engine/models/
[NO ORCHESTRATION, SEPARATE ENVIRONMENT]

AFTER:
User Clicks "Train XRP-BTC Model"
    ↓
POST /api/ml/train (Express Backend)
    ├─ Body: { project: 'xrp-btc', model: 'xgb' }
    │
    ▼
mlRoutes.js → spawns Python subprocess
    ↓
python orchestrator.py --project xrp-btc --model xgb
    ↓
Loads from [UNIFIED] ml-engine/.venv/
    ↓
→ src/pipelines/xrp_btc/train.py
  ├─ Builds features
  ├─ Loads training data
  ├─ Trains model
  └─ Saves to models/xrp_btc/
    ↓
Returns: {"status": "completed", "model": "xgb", "accuracy": 0.87}
    ↓
Frontend receives response + updates UI
[ORCHESTRATED, UNIFIED ENVIRONMENT, TRACKED]
```

---

## Migration Path Timeline

```
PHASE 1: FOUNDATION (Days 1-3)
├─ Day 1: Database schema merge
│   ├─ Backup both databases
│   ├─ Migrate xrp-btc data to crypto_signals DB
│   ├─ Add project/source columns
│   └─ Validate no data loss
├─ Day 2: Environment consolidation
│   ├─ Backup both Python environments
│   ├─ Merge requirements.txt files
│   ├─ Create unified .venv/
│   └─ Test all imports
└─ Day 3: PM2 config unification
    ├─ Backup both ecosystem files
    ├─ Create unified ecosystem.config.js
    ├─ Test individual service starts
    └─ Test pm2 start ecosystem.config.js

PHASE 2: FRONTEND (Days 4-6)
├─ Day 4: Application merge
│   ├─ Merge package.json dependencies
│   ├─ Merge Vite configs
│   ├─ Merge Tailwind configs
│   └─ Test build succeeds
├─ Day 5: Component integration
│   ├─ Create XrpBtcTab.jsx
│   ├─ Add to App.jsx tabs
│   ├─ Create xrpBtcApi.js service
│   └─ Test tab navigation
└─ Day 6: Testing & polish
    ├─ Test all tabs render
    ├─ Test API calls
    ├─ Fix styling
    └─ Cross-browser test

PHASE 3: BACKEND (Days 7-8)
├─ Day 7: Route implementation
│   ├─ Create xrpBtcRoutes.js
│   ├─ Create xrpBtcService.js
│   ├─ Add to server.js
│   └─ Test /api/xrp-btc/* endpoints
└─ Day 8: Integration & testing
    ├─ Test database queries
    ├─ Test error handling
    ├─ Verify CORS headers
    └─ Load testing

PHASE 4: ML & DEPLOYMENT (Days 9-10)
├─ Day 9: ML consolidation
│   ├─ Restructure ml-engine/
│   ├─ Create orchestrator.py
│   ├─ Organize pipelines/
│   └─ Test both train paths
└─ Day 10: Final integration
    ├─ End-to-end testing
    ├─ Docker build & test
    ├─ Documentation review
    └─ Deploy & validate

TOTAL: 10 working days (~2 weeks)
```

---

## Success Indicators

```
✓ FOUNDATION PHASE SUCCESS:
  • All data migrated without loss
  • PM2 starts all services in single command
  • Unified .env works for all services
  
✓ FRONTEND PHASE SUCCESS:
  • All 4+ tabs visible in UI
  • No console errors
  • XrpBtcTab renders with data
  • Styling consistent

✓ BACKEND PHASE SUCCESS:
  • All /api/* endpoints respond
  • Database queries return expected data
  • XRP-BTC data flows to frontend
  • No duplicate requests

✓ ML PHASE SUCCESS:
  • Training works for both projects
  • Models save correctly
  • Orchestrator handles both pipelines
  • End-to-end flow works

✓ DEPLOYMENT PHASE SUCCESS:
  • Docker Compose builds
  • Single docker-compose up launches all services
  • No configuration needed
  • Ready for production
```

