# CryptoTrader Codebase Unification Analysis

## Current State: Multiple Standalone Projects

The workspace contains **two major parallel projects** with duplicated architecture:

### Project 1: `crypto-signals` (Main Umbrella - ACTIVE)
**Location:** `c:\CryptoTrader\next_version\crypto-signals\`

**Services:**
- `backend-engine/` - Express.js REST API (Node.js)
  - Handles: signals, meme tokens, portfolios, quant metrics, PumpX data
  - Port: 4000
  - DB: PostgreSQL
  
- `frontend-engine/` - React + Vite SPA
  - Multiple tabs: Signals, Meme, PumpX Radar, ML Training, Alerts, Trends, Charts
  - Port: 5173
  - Proxies to backend at 4000
  
- `signal-engine/` - TypeScript signal processor
  - Core signal generation logic
  - Meme token signal generation
  - Reads/writes to PostgreSQL
  
- `quant-engine/` - Portfolio metrics processor
  - Calculates portfolio statistics (mean, std dev, sharpe, drawdown)
  - Runs on interval, updates database
  
- `pumpx-streamer-engine/` - WebSocket data streamer
  - Real-time PumpFun token data via Socket.IO
  - Port: 4101
  
- `ml/` - Python ML pipeline
  - `data_ingestion/` - Pump.fun live data ingestion
  - XGBoost training for PumpX signals
  - Transformer models
  - Triggered via REST API from frontend

**Process Manager:** PM2 (via `ecosystem.config.js` or `python-ml-pm2-ecosystem.config.js`)

**Environment:** Node modules installed at root

---

### Project 2: `xrp-btc-spread` (Standalone - LEGACY)
**Location:** `c:\CryptoTrader\next_version\crypto-signals\xrp-btc-spread\`

**Services:**
- `backend-engine/` - Python backend
  - XRP-BTC spread analysis
  - Port: (unspecified)
  
- `frontend-engine/` - React frontend
  - Similar to main project frontend
  - Port: (unspecified)
  
- `ml-engine/` - Python ML
  - XGBoost training (`train_xgb_pg.py`)
  - Transformer training (`train_transformer_v2.py`)
  - Feature building (`feature_builder_v2.py`)
  - Uses virtual env: `venv/`

**Process Manager:** Individual `.bat` scripts (`run_backend.bat`, `run_frontend.bat`, `run_ml.bat`)

**Environment:** Separate Python venv, npm installation in frontend

---

## Key Duplications Identified

### 1. **Frontend Duplication**
| Aspect | Main | XRP-BTC |
|--------|------|---------|
| Framework | React + Vite | React (npm) |
| Location | `frontend-engine/src/` | `xrp-btc-spread/frontend-engine/` |
| Tailwind CSS | ✓ | ✓ |
| Socket.IO | ✓ | ✓ |
| Charts | Recharts | (likely same) |
| Services Layer | `src/services/` | `services/` |

### 2. **Backend Duplication**
| Aspect | Main | XRP-BTC |
|--------|------|---------|
| Language | Node.js (Express) | Python |
| DB | PostgreSQL | PostgreSQL (likely) |
| Port | 4000 | (unspecified) |
| Routes Pattern | REST `/api/*` | (unspecified) |

### 3. **ML Pipeline Duplication**
| Aspect | Main | XRP-BTC |
|--------|------|---------|
| Framework | XGBoost + Transformer | XGBoost + Transformer |
| Data | PumpX tokens | XRP-BTC pairs |
| Feature Builder | `ml/` | `ml-engine/feature_builder_v2.py` |
| Training Scripts | `train_pumpx_xgb.py` | `train_xgb_pg.py`, `train_transformer_v2.py` |
| Environment | `.venv-ml/` | `venv/` |

### 4. **Database Layer Duplication**
- Both use PostgreSQL
- Schema likely similar (tokens, signals, metrics, alerts)
- Connection pooling needed for unified approach

### 5. **Process Management Duplication**
| Aspect | Main | XRP-BTC |
|--------|------|---------|
| PM2 Config | `ecosystem.config.js` | `.bat` scripts |
| Start Scripts | `.ps1` files in each engine | `.bat` files |
| Logging | PM2 managed | (none visible) |

---

## Unification Strategy

### Phase 1: Consolidate Process Management
**Action:** Merge both projects' services into single PM2 ecosystem
```
Root ecosystem.config.js:
├── Backend (crypto-signals)
├── Frontend (crypto-signals)
├── Signal Engine
├── Quant Engine
├── PumpX Streamer
├── ML Pipeline (crypto-signals)
├── [OPTIONAL] Backend (xrp-btc-spread)
├── [OPTIONAL] ML Pipeline (xrp-btc-spread)
```

### Phase 2: Unify Frontend Architecture
**Action:** Migrate xrp-btc-spread frontend into main frontend with new tab
- Consolidate Vite configs
- Merge component libraries
- Unified service layer
- Single node_modules at root

### Phase 3: Unify Database Schema
**Action:** Create unified PostgreSQL schema
- Migrate xrp-btc-spread tables to crypto-signals DB
- Create views/tables for both token types
- Ensure foreign key relationships

### Phase 4: Consolidate ML Pipeline (Optional)
**Action:** Unify Python ML infrastructure
- Merge `.venv-ml/` and `venv/`
- Consolidate feature builders
- Single training orchestration
- Create generic training interface (pumpx vs xrp-btc vs others)

### Phase 5: Unify Backend API
**Action:** Migrate xrp-btc-spread backend to Node.js or add routes to main backend
- Add `/api/xrp-btc/*` routes to crypto-signals backend
- Reuse middleware (auth, CORS, logging)
- Unified error handling

---

## Recommended Directory Structure (Post-Unification)

```
crypto-signals/
├── package.json (workspace root)
├── ecosystem.config.js (unified PM2 config)
├── docker-compose.yml (unified services)
├── .env (unified environment)
│
├── services/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   │   ├── signals.js
│   │   │   │   ├── meme.js
│   │   │   │   ├── pumpx.js
│   │   │   │   ├── xrp-btc.js (NEW - consolidated)
│   │   │   │   └── ...
│   │   │   ├── services/
│   │   │   ├── db.js
│   │   │   └── server.js
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── tabs/
│   │   │   │   ├── SignalsTab.jsx
│   │   │   │   ├── PumpxTab.jsx
│   │   │   │   ├── XrpBtcTab.jsx (NEW - consolidated)
│   │   │   │   └── ...
│   │   │   ├── services/
│   │   │   ├── components/
│   │   │   └── App.jsx
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── signal-engine/
│   ├── quant-engine/
│   ├── pumpx-streamer-engine/
│   │
│   └── ml-engine/
│       ├── src/
│       │   ├── pipelines/
│       │   │   ├── pumpx/
│       │   │   └── xrp-btc/ (NEW - consolidated)
│       │   ├── models/
│       │   ├── features/
│       │   └── utils/
│       ├── requirements.txt
│       └── .venv/
│
├── shared/
│   ├── types/ (TypeScript types used by multiple services)
│   ├── schemas/ (Database schemas)
│   ├── utils/
│   └── config/
│
├── ops/
│   ├── docker/
│   ├── k8s/
│   └── scripts/
│
└── docs/
    ├── ARCHITECTURE.md
    ├── API.md
    ├── DB_SCHEMA.md
    └── DEPLOYMENT.md
```

---

## Integration Points to Consider

### 1. **Database**
- Single PostgreSQL instance
- Unified user/password in `.env`
- Schema migrations for both projects
- Connection pooling at root level

### 2. **Frontend Routing**
```javascript
// App.jsx - unified tab system
const TABS = {
  signals: SignalsTab,
  meme: MemeTab,
  pumpx: PumpxRadarTab,
  'xrp-btc': XrpBtcTab,  // NEW
  settings: SettingsTab
};
```

### 3. **Backend Routing**
```javascript
// server.js - unified API
app.use('/api/signals', signalsRoutes);
app.use('/api/meme', memeRoutes);
app.use('/api/pumpx', pumpxRoutes);
app.use('/api/xrp-btc', xrpBtcRoutes);  // NEW
```

### 4. **ML Pipeline**
```python
# ml_orchestrator.py - unified entry point
def train_model(pair_type, model_type, **kwargs):
    if pair_type == 'pumpx':
        return train_pumpx(model_type, **kwargs)
    elif pair_type == 'xrp-btc':
        return train_xrp_btc(model_type, **kwargs)
```

### 5. **Environment Configuration**
```env
# .env - unified config
DATABASE_URL=postgresql://user:pass@localhost/crypto_signals
REDIS_URL=redis://localhost:6379

# Backend
PORT=4000

# Frontend
VITE_BACKEND_HTTP=http://localhost:4000

# ML
ML_PYTHON_PATH=./ml-engine/.venv/Scripts/python.exe
ML_OUTPUT_DIR=./ml-engine/models

# Data sources
PUMPFUN_RPC=https://...
BINANCE_API_KEY=...

# Feature flags
ENABLE_XRP_BTC=true
ENABLE_PUMPX=true
```

---

## Migration Checklist

- [ ] **Backup** both projects
- [ ] **Document** current xrp-btc-spread deployment (which services are running?)
- [ ] **Unify** database schema and migrate data
- [ ] **Merge** PM2 configurations
- [ ] **Consolidate** node_modules (or use monorepo with yarn workspaces/npm workspaces)
- [ ] **Migrate** xrp-btc backend routes to Node.js or add as Node.js service
- [ ] **Merge** frontend applications
- [ ] **Consolidate** ML Python environment
- [ ] **Create** unified Docker setup
- [ ] **Test** all services together
- [ ] **Deploy** unified stack
- [ ] **Archive** old xrp-btc-spread structure

---

## Quick Start After Unification

```bash
# Install all dependencies
npm install

# Set up shared Python environment
cd services/ml-engine
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Start all services
pm2 start ecosystem.config.js

# Or run individually
npm run dev:backend
npm run dev:frontend
npm run dev:ml
```

