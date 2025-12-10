# CryptoTrader Unification: Migration Checklist & File Mappings

## Quick Reference: What Goes Where

### XRP-BTC Frontend Files → Main Frontend

```
SOURCE: xrp-btc-spread/frontend-engine/
DEST: frontend-engine/

MIGRATE THESE FILES:
├── src/
│   ├── components/          → frontend-engine/src/components/xrpbtc/
│   ├── hooks/              → frontend-engine/src/hooks/ (if unique)
│   ├── services/           → Merge into frontend-engine/src/services/
│   │   ├── xrpBtcApi.js    ← NEW API service wrapper
│   │   └── *.js            ← Check for duplication with existing
│   ├── styles/             → Review and merge into frontend-engine/src/styles.css
│   └── utils/              → Merge into frontend-engine/src/utils/
│
├── tailwind.config.js       → Merge with frontend-engine/tailwind.config.js
├── package.json             → Merge dependencies into frontend-engine/package.json
└── vite.config.js           → Merge with frontend-engine/vite.config.js

REMOVE:
├── node_modules/            ← Delete (use unified)
├── package-lock.json        ← Delete (use unified)
└── run_frontend.bat          ← Delete (use main ecosystem)
```

### XRP-BTC Backend Files → Main Backend

```
SOURCE: xrp-btc-spread/backend-engine/
DEST: backend-engine/

MIGRATE THESE FILES:
├── services/
│   └── *.py                 → backend-engine/src/services/xrpbtc/ (as reference)
│       ├── Convert to JavaScript/Node.js
│       ├── Or create routes/xrpBtc.js that calls Python subprocess
│       └── Note: XRP-BTC backend is Python, main is Node.js
│
├── requirements.txt         → Merge into services/ml-engine/requirements.txt
└── run_backend.bat          → Delete (use main ecosystem)

CONSIDER:
- Rewrite xrp-btc-spread backend in Node.js (recommended)
- OR create Python subprocess wrapper in Node.js backend
- OR keep Python backend running separately on different port
```

### XRP-BTC ML Files → Unified ML

```
SOURCE: xrp-btc-spread/ml-engine/
DEST: services/ml-engine/ (after creating unified structure)

MIGRATE THESE FILES:
├── feature_builder_v2.py
│   → services/ml-engine/src/features/xrp_btc_features.py

├── train_xgb_pg.py
│   → services/ml-engine/src/models/xgb_xrp_btc.py
│   → Or refactor into services/ml-engine/src/models/xgb.py (shared)

├── train_transformer_v2.py
│   → services/ml-engine/src/models/transformer_xrp_btc.py
│   → Or refactor into services/ml-engine/src/models/transformer.py (shared)

├── models/
│   → services/ml-engine/models/xrp_btc/

├── historical/
│   → services/ml-engine/data/xrp_btc/

└── sql-scripts/
    → services/ml-engine/sql/xrp_btc_schema.sql

DELETE:
├── venv/                    ← Delete (use .venv-ml/ merged)
├── requirements.txt         ← Merge into shared requirements.txt
├── run_ml.bat              ← Delete (use main ecosystem)
└── __pycache__/            ← Delete (auto-generated)
```

---

## Step-by-Step Migration Process

### STEP 1: Database Migration

```sql
-- Add new columns to support both projects in single DB
ALTER TABLE tokens ADD COLUMN project VARCHAR(50);
ALTER TABLE tokens ADD COLUMN source VARCHAR(50);
CREATE INDEX idx_tokens_project ON tokens(project);

-- Create xrp-btc specific tables (or use unified schema)
CREATE TABLE IF NOT EXISTS xrp_btc_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    xrp_price DECIMAL(18,8),
    btc_price DECIMAL(18,8),
    spread DECIMAL(18,8),
    rsi DECIMAL(10,8),
    macd DECIMAL(10,8),
    prediction DECIMAL(10,8),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Migrate xrp-btc-spread data
INSERT INTO tokens (symbol, name, project, source)
SELECT symbol, name, 'xrp-btc', 'xrp-btc-spread'
FROM xrp_btc_spread_db.tokens
WHERE NOT EXISTS (SELECT 1 FROM tokens t WHERE t.symbol = symbol);
```

### STEP 2: Backend Integration

**Option A: Rewrite XRP-BTC Backend in Node.js** (RECOMMENDED)

```javascript
// backend-engine/src/routes/xrpBtc.js
import express from "express";
import { query } from "../db.js";

export const router = express.Router();

router.get("/metrics", async (req, res) => {
    try {
        const rows = await query(
            `SELECT * FROM xrp_btc_metrics ORDER BY timestamp DESC LIMIT 100`
        );
        res.json(rows);
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "metrics query failed" });
    }
});

router.post("/train", async (req, res) => {
    // Trigger ML training via API
    try {
        // Call ML service or spawn Python process
        res.json({ status: "training started" });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

export default router;
```

```javascript
// backend-engine/src/server.js - add route
import xrpBtcRoutes from "./routes/xrpBtc.js";
app.use("/api/xrp-btc", xrpBtcRoutes);
```

**Option B: Keep Python Backend, Add Node.js Proxy**

```javascript
// backend-engine/src/routes/xrpBtc.js
import fetch from "node-fetch";

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || "http://localhost:5000";

router.get("/metrics", async (req, res) => {
    try {
        const response = await fetch(`${PYTHON_BACKEND_URL}/metrics`);
        const data = await response.json();
        res.json(data);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});
```

### STEP 3: Frontend Tab Integration

```javascript
// frontend-engine/src/App.jsx
import XrpBtcTab from "./tabs/XrpBtcTab.jsx";

export default function App() {
  const [activeTab, setActiveTab] = useState("signals");

  const tabs = {
    signals: { label: "Signals", component: CoreSignalsTab },
    meme: { label: "Meme", component: MemeTab },
    pumpx: { label: "PumpX", component: PumpxRadarTab },
    "xrp-btc": { label: "XRP-BTC", component: XrpBtcTab },  // ← NEW
    settings: { label: "Settings", component: SettingsTab }
  };

  return (
    <div>
      <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />
      {React.createElement(tabs[activeTab]?.component)}
    </div>
  );
}
```

```javascript
// frontend-engine/src/tabs/XrpBtcTab.jsx (NEW)
import React, { useState, useEffect } from "react";
import { getXrpBtcMetrics } from "../services/xrpBtcApi.js";

export default function XrpBtcTab() {
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await getXrpBtcMetrics();
        setMetrics(data);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="tab">
      <h2>XRP-BTC Spread Analysis</h2>
      {loading ? <p>Loading...</p> : <MetricsTable metrics={metrics} />}
    </div>
  );
}
```

```javascript
// frontend-engine/src/services/xrpBtcApi.js (NEW)
const API_BASE = "/api/xrp-btc";

export async function getXrpBtcMetrics() {
    const response = await fetch(`${API_BASE}/metrics`);
    return response.json();
}

export async function trainModel() {
    const response = await fetch(`${API_BASE}/train`, { method: "POST" });
    return response.json();
}

export default {
    getXrpBtcMetrics,
    trainModel
};
```

### STEP 4: ML Pipeline Unification

```python
# services/ml-engine/src/orchestrator.py (NEW)
import sys
import argparse
from pipelines.pumpx.train import train_pumpx_model
from pipelines.xrp_btc.train import train_xrp_btc_model

def train_model(project_type, model_type, **kwargs):
    """
    Unified training orchestrator
    
    Args:
        project_type: 'pumpx' or 'xrp-btc'
        model_type: 'xgb' or 'transformer'
    """
    if project_type == 'pumpx':
        return train_pumpx_model(model_type, **kwargs)
    elif project_type == 'xrp-btc':
        return train_xrp_btc_model(model_type, **kwargs)
    else:
        raise ValueError(f"Unknown project type: {project_type}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="pumpx or xrp-btc")
    parser.add_argument("--model", required=True, help="xgb or transformer")
    args = parser.parse_args()
    
    train_model(args.project, args.model)
```

```python
# services/ml-engine/src/pipelines/xrp_btc/train.py (NEW)
# Migrated from xrp-btc-spread/ml-engine/train_xgb_pg.py

import sys
sys.path.insert(0, '/path/to/unified/ml-engine')

from src.models.xgb import XGBModel
from src.features.xrp_btc_features import build_xrp_btc_features
from src.utils.db import get_connection

def train_xrp_btc_model(model_type='xgb', **kwargs):
    """Train XRP-BTC spread model"""
    
    # Load features
    features = build_xrp_btc_features()
    
    # Train model
    if model_type == 'xgb':
        model = XGBModel()
        model.train(features)
        model.save('models/xrp_btc/xgb_latest.pkl')
    
    return {"status": "completed", "model_type": model_type}
```

### STEP 5: Environment Consolidation

```bash
# Create unified Python environment
cd services/ml-engine
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Unified requirements.txt
psycopg2-binary==2.9.9
pandas==2.1.0
scikit-learn==1.3.0
xgboost==2.0.0
numpy==1.24.0
torch==2.0.0
transformers==4.30.0
python-dotenv==1.0.0
requests==2.31.0
```

### STEP 6: PM2 Configuration Update

```javascript
// ecosystem.config.js (UNIFIED)
module.exports = {
  apps: [
    {
      name: "backend",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/backend-engine",
      script: "npm",
      args: "start",
      autorestart: true,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/backend-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/backend-error.log"
    },
    {
      name: "frontend",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/frontend-engine",
      script: "npm",
      args: "run dev",
      autorestart: true,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/frontend-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/frontend-error.log"
    },
    {
      name: "signal-engine",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/signal-engine",
      script: "npm",
      args: "start",
      autorestart: true,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/signal-engine-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/signal-engine-error.log"
    },
    {
      name: "quant-engine",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/quant-engine",
      script: "npm",
      args: "start",
      autorestart: true,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/quant-engine-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/quant-engine-error.log"
    },
    {
      name: "pumpx-streamer",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/pumpx-streamer-engine",
      script: "npm",
      args: "start",
      autorestart: true,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx-streamer-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx-streamer-error.log"
    }
    // No separate xrp-btc services - integrated into main backend
  ]
};
```

---

## File Deletion Checklist (After Migration)

After successfully migrating, DELETE these directories to avoid confusion:

```
DELETE:
☐ xrp-btc-spread/               (entire folder)
  ☐ xrp-btc-spread/backend-engine/
  ☐ xrp-btc-spread/frontend-engine/
  ☐ xrp-btc-spread/ml-engine/
  ☐ xrp-btc-spread/README_ml_v2.txt
  ☐ xrp-btc-spread/*.bat files
  ☐ xrp-btc-spread/*.py files

KEEP (for reference):
✓ xrp-btc-spread/ (as a backup archive)
  OR move to: temp/xrp-btc-spread-archive/
```

---

## Validation Checklist

After each migration step, verify:

### Frontend
- [ ] All tabs load without errors
- [ ] XrpBtcTab component renders
- [ ] API calls to /api/xrp-btc/* work
- [ ] No console errors
- [ ] Styling consistent with other tabs

### Backend
- [ ] `npm start` launches without errors
- [ ] `GET /api/xrp-btc/metrics` returns data
- [ ] Database queries work
- [ ] CORS allows frontend requests
- [ ] Logging shows requests

### Database
- [ ] xrp_btc_metrics table exists
- [ ] New token records inserted
- [ ] Old xrp-btc-spread DB data migrated
- [ ] Indexes created
- [ ] No duplicate records

### ML Pipeline
- [ ] Python environment installed
- [ ] `python orchestrator.py --project xrp-btc --model xgb` works
- [ ] Models save to correct location
- [ ] Training data loads successfully

### PM2
- [ ] `pm2 start ecosystem.config.js` starts all services
- [ ] No errors in pm2 logs
- [ ] `pm2 stop all` stops all services
- [ ] `pm2 monit` shows all services healthy

---

## Rollback Plan

If issues arise during migration:

```bash
# Restore xrp-btc-spread from archive
tar -xzf xrp-btc-spread-backup.tar.gz

# Restore database from backup
pg_restore -d crypto_signals xrp-btc-spread_db_backup.sql

# Revert frontend changes
git checkout frontend-engine/

# Revert backend changes
git checkout backend-engine/

# Restart original PM2 configs
pm2 delete ecosystem
pm2 start python-ml-pm2-ecosystem.config.js
```

