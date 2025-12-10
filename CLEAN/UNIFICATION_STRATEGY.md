# CryptoTrader Unification: Side-by-Side Comparison

## System Architecture Comparison

### Current State (Two Separate Systems)

```
┌─────────────────────────────────────────────┐
│          CRYPTO-SIGNALS PROJECT             │
├─────────────────────────────────────────────┤
│  Frontend (React+Vite)                      │
│  └─ Port 5173                               │
│  Backend (Express)                          │
│  └─ Port 4000                               │
│  Signal Engine (TypeScript)                 │
│  Quant Engine (Node.js)                     │
│  PumpX Streamer (Socket.IO)                 │
│  ML Engine (Python)                         │
│  └─ .venv-ml/ environment                   │
│  Database (PostgreSQL)                      │
│  └─ tokens, signals, metrics, alerts        │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│          XRP-BTC-SPREAD PROJECT             │
│  (Currently inside crypto-signals folder)   │
├─────────────────────────────────────────────┤
│  Frontend (React)                           │
│  Backend (Python)                           │
│  ML Engine (Python)                         │
│  └─ venv/ environment (SEPARATE)            │
│  Database (PostgreSQL - separate?)          │
│  └─ xrp, btc pairs data                     │
└─────────────────────────────────────────────┘

     [NO DIRECT INTEGRATION - PARALLEL]
```

### Proposed Unified State

```
┌──────────────────────────────────────────────────┐
│     UNIFIED CRYPTO-SIGNALS PLATFORM              │
├──────────────────────────────────────────────────┤
│                                                  │
│  FRONTEND LAYER (Single SPA)                     │
│  ├─ Signals Tab      (Existing)                  │
│  ├─ Meme Tab         (Existing)                  │
│  ├─ PumpX Tab        (Existing)                  │
│  └─ XRP-BTC Tab      (← MIGRATED)               │
│                                                  │
│  API GATEWAY (Express - Port 4000)               │
│  ├─ /api/signals        ┐                       │
│  ├─ /api/meme           ├─ Signal Routes        │
│  ├─ /api/pumpx          ┤                       │
│  └─ /api/xrp-btc        ┘ (← ADDED)             │
│  ├─ /api/quant                                  │
│  └─ /api/ml                                     │
│                                                  │
│  BACKGROUND SERVICES                            │
│  ├─ Signal Engine (TypeScript)                  │
│  ├─ Quant Engine (Node.js)                      │
│  └─ PumpX Streamer (Socket.IO)                  │
│                                                  │
│  ML ORCHESTRATOR (Unified Python)               │
│  ├─ PumpX Pipeline                              │
│  └─ XRP-BTC Pipeline (← MIGRATED)              │
│                                                  │
│  SHARED DATABASE LAYER                          │
│  └─ Single PostgreSQL Instance                  │
│     ├─ tokens (pumpx, xrp, btc)                │
│     ├─ signals (unified schema)                │
│     ├─ metrics (portfolios, spreads)           │
│     ├─ alerts (all sources)                    │
│     └─ ml_models (versions)                    │
│                                                  │
│  UNIFIED ENVIRONMENT                            │
│  ├─ Single Python .venv/                        │
│  ├─ Single node_modules/                        │
│  ├─ Single .env configuration                   │
│  └─ Single PM2 ecosystem                        │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## Component Migration Map

### 1. Frontend Components

**FROM xrp-btc-spread/frontend-engine →  TO crypto-signals/frontend-engine**

```
xrp-btc-spread/frontend-engine/
├── package.json
├── src/
│   ├── App.jsx               → Merge into main App.jsx (add XrpBtcTab)
│   ├── services/
│   │   └── *.js              → Merge into frontend-engine/src/services/
│   └── components/           → Merge or rename as XrpBtc-specific

crypto-signals/frontend-engine/
├── package.json              ← Becomes unified package.json
└── src/
    ├── App.jsx              ← Updated with XrpBtcTab
    ├── tabs/
    │   ├── SignalsTab.jsx    (existing)
    │   ├── MemeTab.jsx       (existing)
    │   ├── PumpxTab.jsx      (existing)
    │   └── XrpBtcTab.jsx     ← NEW (from xrp-btc-spread)
    ├── services/
    │   ├── api.js            (existing)
    │   ├── pumpxApi.js       (existing)
    │   └── xrpBtcApi.js      ← NEW (from xrp-btc-spread)
    └── components/
        ├── pumpx/            (existing)
        └── xrpbtc/           ← NEW (from xrp-btc-spread)
```

### 2. Backend Routes

**FROM xrp-btc-spread/backend-engine →  TO crypto-signals/backend-engine**

```
xrp-btc-spread/backend-engine/          → crypto-signals/backend-engine/src/routes/
├── services/           ─┐
└── routes/ (implicit)  ─┼─→ xrpBtcRoutes.js (NEW)
                        
crypto-signals/backend-engine/src/
├── routes/
│   ├── signals.js       (existing)
│   ├── meme.js          (existing)
│   ├── pumpx.js         (existing)
│   ├── timeframes.js    (existing)
│   ├── portfolios.js    (existing)
│   └── xrpBtc.js        ← NEW (created from xrp-btc backend logic)
│
├── services/
│   ├── signalService.js (existing)
│   ├── pumpxService.js  (existing)
│   └── xrpBtcService.js ← NEW (from xrp-btc services/)
│
└── server.js           ← Updated to include xrp-btc routes
    app.use('/api/xrp-btc', xrpBtcRoutes)
```

### 3. Database Schema

**UNIFIED PostgreSQL DATABASE**

```
BEFORE (Two separate DBs or schemas):
xrp_btc_spread_db/          crypto_signals_db/
├── xrp_metrics              ├── meme_tokens
├── btc_metrics              ├── meme_signals
├── xrp_btc_alerts           ├── meme_alpha_signals
└── predictions              ├── pumpx_live
                             ├── pumpx_radar
                             └── portfolios

AFTER (Single unified DB):
crypto_signals_unified/
├── tokens (unified)
│   ├── id, symbol, name
│   ├── type (ENUM: 'meme', 'pumpx', 'xrp', 'btc', 'other')
│   └── source (ENUM: 'pumpfun', 'binance', etc)
│
├── signals
│   ├── id, token_id, signal_type, value, confidence
│   ├── signal_source (ENUM: 'core', 'alpha', 'pumpx', 'xrp_btc')
│   └── timestamp, created_at
│
├── xrp_btc_metrics          ← NEW (from xrp-btc-spread)
│   ├── timestamp
│   ├── xrp_price, btc_price, spread
│   ├── rsi, macd, bollinger
│   └── prediction
│
├── alerts
│   ├── id, alert_type, level, message
│   ├── related_token_id (nullable)
│   └── timestamp
│
└── ml_models
    ├── id, name, type (xgb, transformer, etc)
    ├── target (pumpx, xrp_btc, etc)
    ├── accuracy, created_at, deployed
    └── model_path
```

### 4. ML Pipeline

**FROM xrp-btc-spread/ml-engine →  TO crypto-signals/ml-engine**

```
xrp-btc-spread/ml-engine/
├── feature_builder_v2.py    → ml-engine/src/features/xrp_btc_features.py
├── train_xgb_pg.py          → ml-engine/src/models/xgb.py
├── train_transformer_v2.py  → ml-engine/src/models/transformer.py
├── models/                  → ml-engine/models/xrp_btc/
└── venv/                    [MERGED into single .venv/]

crypto-signals/ml-engine/
├── src/
│   ├── pipelines/
│   │   ├── pumpx/
│   │   │   ├── data_ingestion.py
│   │   │   ├── features.py
│   │   │   └── train.py
│   │   └── xrp_btc/          ← NEW (from xrp-btc-spread)
│   │       ├── data_ingestion.py
│   │       ├── features.py
│   │       └── train.py
│   │
│   ├── features/
│   │   ├── pumpx_features.py
│   │   └── xrp_btc_features.py  ← NEW
│   │
│   ├── models/
│   │   ├── xgb.py
│   │   ├── transformer.py
│   │   └── base.py (shared)
│   │
│   └── orchestrator.py       ← NEW unified entry point
│       def train_model(pair_type, model_type, **kwargs)
│
├── models/                   ← Unified model storage
│   ├── pumpx/
│   ├── xrp_btc/              ← NEW
│   └── shared/
│
├── requirements.txt          ← Unified (merged from both)
└── .venv/                    ← Single Python environment
```

---

## Development Workflow After Unification

### Install & Setup
```bash
cd crypto-signals
npm install                                    # Install all Node services
cd services/ml-engine && python -m venv .venv # Python ML environment
.\.venv\Scripts\pip install -r requirements.txt
```

### Development (All Services)
```bash
# Terminal 1: All services via PM2
pm2 start ecosystem.config.js

# Terminal 2: Frontend dev server with hot reload
npm --prefix services/frontend run dev

# Terminal 3: Backend dev server
npm --prefix services/backend run dev

# Terminal 4: ML pipeline (if testing)
cd services/ml-engine && python src/orchestrator.py
```

### Adding New Feature
```bash
# Example: Add new token type "solana"

1. Database: Add ENUM value 'solana' to tokens.type
2. Backend: Create services/backend/src/routes/solana.js
3. Frontend: Create services/frontend/src/tabs/SolanaTab.jsx
4. App: Import and add to tabs in App.jsx
5. API service: Add to services/frontend/src/services/solanaApi.js
6. ML (optional): Create services/ml-engine/src/pipelines/solana/
```

---

## Deployment Architecture After Unification

### Single Docker Compose
```yaml
services:
  postgres:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
  
  backend:
    build: ./services/backend
    ports:
      - "4000:4000"
    depends_on:
      - postgres
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/crypto
  
  frontend:
    build: ./services/frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
  
  signal-engine:
    build: ./services/signal-engine
    depends_on:
      - postgres
  
  ml-engine:
    build: ./services/ml-engine
    depends_on:
      - postgres
      - backend
    volumes:
      - ./services/ml-engine/models:/app/models
```

### PM2 Single Ecosystem
```javascript
module.exports = {
  apps: [
    {
      name: "backend",
      cwd: "./services/backend",
      script: "npm run start"
    },
    {
      name: "frontend",
      cwd: "./services/frontend",
      script: "npm run dev"
    },
    {
      name: "signal-engine",
      cwd: "./services/signal-engine",
      script: "npm start"
    },
    {
      name: "quant-engine",
      cwd: "./services/quant-engine",
      script: "npm start"
    },
    {
      name: "pumpx-streamer",
      cwd: "./services/pumpx-streamer-engine",
      script: "npm start"
    }
  ]
};
```

---

## Benefits of Unification

| Benefit | Impact |
|---------|--------|
| **Single DB** | Easier cross-project queries, unified backups |
| **Unified API** | Consistent error handling, auth, middleware |
| **Shared Frontend** | Reduced bundle size, code duplication elimination |
| **Single ML Env** | Simplified deployment, shared model versioning |
| **Unified Config** | One `.env` file, easier environment management |
| **PM2 Control** | Start/stop all services together, unified logging |
| **Docker Compose** | Single-command deployment |
| **Code Reuse** | Services/utilities shared across projects |
| **Maintenance** | Bug fixes applied to all projects at once |

---

## Migration Priority

### Phase 1 (Week 1): Foundation
- Merge PM2 configs
- Unify database schema
- Set up shared Python environment

### Phase 2 (Week 2): Frontend
- Consolidate frontend apps
- Merge component libraries
- Test all tabs together

### Phase 3 (Week 3): Backend
- Migrate xrp-btc routes to Node.js
- Add to unified API
- Update frontend API calls

### Phase 4 (Week 4): ML & Testing
- Merge ML pipelines
- Test end-to-end
- Documentation

