# CryptoTrader V2: Quick Reference Guide

## 📌 One-Page Overview

**What:** Completely new modular trading platform (V2)  
**Why:** Current system scattered, need unified architecture for scalability  
**Where:** NEW folder `crypto-signals-v2/` (doesn't touch existing code)  
**When:** 9 weeks to production  
**Who:** Backend (Python), Frontend (React), ML Engineer, DevOps  

---

## 🎯 Three Core Dashboards

### 1️⃣ Trading Dashboard (For Traders)
- Live signals board with confidence scores
- Real-time portfolio & PnL tracking
- Active positions with one-click management
- Charts with technical indicators
- Alert subscription management

**Technology:** React + Vite + Tailwind

### 2️⃣ Admin Dashboard (For Admins/Config)
- System settings & risk parameters
- Wallet management (add/edit exchange keys - encrypted)
- Integration setup (Telegram, Email, Webhooks, Discord)
- ML model upload & version management
- User management & permissions
- System monitoring & health checks

**Technology:** React + Vite + Tailwind

### 3️⃣ Shared Theme System
- Unified design system across both dashboards
- Consistent colors, fonts, spacing
- Reusable React components
- Dark/light mode support

---

## 🧠 ML Models (80-85% Confidence Target)

### Predictive Model
```
Input:  OHLC price data (200 candles)
        + Technical features (RSI, MACD, Bollinger, momentum)
        
Process: XGBoost + LightGBM ensemble
        + Voting mechanism
        + 2-year backtest validation
        
Output: BUY / SELL / HOLD
        + Confidence score (0-1)
        + Entry/SL/TP levels
        
Target: 80-85% accuracy
        + Precision >80%
        + Recall >75%
```

### Alpha Model (100X Spotting)
```
Input:  Market trends
        + Social media sentiment (Twitter/Discord)
        + On-chain data (whale, liquidity)
        + Anomaly patterns
        
Process: Multi-source scoring
        (30% trend + 30% sentiment + 25% on-chain + 15% anomaly)
        
Output: Alpha score (0-1)
        + Emerging token recommendations
        
Alert when: Alpha score >0.80
```

---

## 🏗️ Services Architecture

### Backend Services (to build)
```
1. API Gateway (Node.js + Express)
   - REST API: /api/signals, /api/trading, /api/admin
   - WebSocket: Real-time updates
   - Auth: JWT tokens

2. Signal Engine (Python)
   - Runs ML models every 5 minutes
   - Generates predictions & alpha scores
   - Stores in database

3. Trading Engine (Python)
   - Auto-trades on signals (confidence >80%)
   - Position sizing (risk-based)
   - SL/TP management

4. Notification Service (Node.js + Python)
   - Telegram alerts
   - Email notifications
   - Webhook dispatching

5. Data Aggregator (Python)
   - Fetches OHLC from Binance
   - Pulls PumpFun new tokens
   - Indexes DEX activity
```

### Database (Single PostgreSQL)
```
Core tables:
- users (authentication)
- wallets (encrypted exchange keys)
- signals (BUY/SELL + alpha scores)
- trades (active + closed positions)
- portfolios (performance metrics)
- integrations (Telegram config, etc)
- ml_models (versions & accuracy)
```

---

## 📊 Signal Flow

```
1. Data Ingestion
   Binance OHLC → Normalize → Cache

2. Feature Engineering
   Price + Volume → Technical indicators → Features

3. ML Inference
   Features → Predictive Model → 80-85% confidence signal
            OR
   Market data → Alpha Model → 100X opportunity alert

4. Storage
   Signal → PostgreSQL with timestamp + confidence

5. Streaming
   Signal → WebSocket → Dashboard (real-time)

6. Auto-Trading
   High confidence signal → Execute trade if enabled
   ↓
   Position → Track PnL → Close on TP/SL

7. Notifications
   Trade → Telegram/Email/Webhook alerts
```

---

## 🔧 Integration Configuration (Admin Dashboard)

### Telegram Setup
```
1. Create bot with @BotFather
2. Get: Chat ID + Bot Token
3. In Admin Dashboard:
   - Paste Chat ID
   - Paste Bot Token
   - Test connection
   - Enable alerts
```

### Email Setup
```
1. SMTP server: smtp.gmail.com
2. Sender email: your@email.com
3. Password: App password (not regular password)
4. In Admin Dashboard:
   - Enter SMTP config
   - Test send
```

### Webhook Setup
```
1. Create webhook endpoint
2. In Admin Dashboard:
   - Paste webhook URL
   - Select event types (signal, trade, alert)
   - Test with sample payload
```

---

## 📁 Folder Structure (Simplified)

```
crypto-signals-v2/
├── services/
│   ├── api-gateway/        ← REST API, auth, routes
│   ├── signal-engine/      ← ML model serving
│   ├── trading-engine/     ← Auto-trading execution
│   ├── notification-service/  ← Alerts (Telegram, Email)
│   └── data-aggregator/    ← Data ingestion
│
├── dashboards/
│   ├── trading-dashboard/  ← Trader UI
│   └── admin-dashboard/    ← Admin UI
│
├── shared/
│   ├── theme/              ← Unified design
│   ├── components/         ← Reusable React
│   └── utils/              ← Helper functions
│
├── ml/
│   ├── models/
│   │   ├── predictive/     ← Main ML model (80-85%)
│   │   ├── alpha/          ← 100X detector
│   │   └── ensemble/       ← Combined scoring
│   └── notebooks/          ← Jupyter experiments
│
├── db/
│   └── migrations/         ← Schema upgrades
│
└── ops/
    ├── docker-compose.yml  ← Local dev
    └── kubernetes/         ← Production deploy
```

---

## 🚀 Development Phases (9 Weeks)

| Phase | Weeks | Focus | Deliverables |
|-------|-------|-------|--------------|
| 1 | 1-2 | Foundation | DB, API Gateway, Auth |
| 2 | 3-4 | Dashboards | Trading UI, Admin UI, Theme |
| 3 | 5-6 | ML Models | Predictive (80-85%), Alpha |
| 4 | 7 | Signals | Signal Engine, DB persistence |
| 5 | 8 | Trading | Auto-trading, Risk mgmt |
| 6 | 9 | Integration | Telegram, Testing, Deploy |

---

## 💻 Tech Stack

### Backend
- **API:** Express.js (Node.js)
- **Database:** PostgreSQL 15
- **ML:** XGBoost, LightGBM, Scikit-learn, Pandas
- **Trading:** CCXT (exchange API wrapper)
- **Real-time:** Socket.io

### Frontend
- **Framework:** React 18
- **Build:** Vite
- **Styling:** Tailwind CSS
- **State:** Zustand
- **Charts:** Chart.js

### Infrastructure
- **Docker:** Containerization
- **Docker Compose:** Local development
- **Kubernetes:** Production (optional)

---

## ✅ Success Criteria

### ML Model
- [ ] Accuracy: 80-85% on unseen test data
- [ ] Precision >80% (reduce false signals)
- [ ] Sharpe Ratio >1.5 (risk-adjusted)
- [ ] Max drawdown <20%

### System
- [ ] API response time <100ms
- [ ] Signal generation <1 second
- [ ] Trade execution <5 seconds
- [ ] Uptime >99.5%

### User Experience
- [ ] Setup time <10 minutes
- [ ] Dashboard load <2 seconds
- [ ] Real-time alerts <1 minute

---

## 🔐 Security Checklist

- [ ] Database encryption (at rest)
- [ ] Wallet keys encrypted (AES-256)
- [ ] API authentication (JWT)
- [ ] HTTPS only (production)
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] CORS properly configured
- [ ] 2FA for sensitive operations
- [ ] Audit logging (all actions)

---

## 🎓 Key Documents

1. **V2_SUMMARY.md** (this) - High-level overview
2. **V2_ARCHITECTURE.md** - Complete system design
3. **V2_IMPLEMENTATION.md** - Step-by-step code examples
4. **API.md** (to create) - Endpoint documentation
5. **ML-MODELS.md** (to create) - Model details & tuning

---

## 🚨 Important Notes

### ✅ DO
- Create completely new `crypto-signals-v2/` folder
- Follow the modular structure (easy to add services)
- Use the shared theme system (consistent UX)
- Encrypt all sensitive data (keys, passwords)
- Test ML models before auto-trading
- Document all integrations

### ❌ DON'T
- Touch existing codebase (leave it as-is)
- Hardcode secrets (use .env)
- Skip the testing phase (especially ML models)
- Auto-trade with confidence <80%
- Store unencrypted wallet keys
- Rush to production

---

## 🎯 First Steps

1. **Read Documentation**
   - [ ] V2_SUMMARY.md (this file)
   - [ ] V2_ARCHITECTURE.md (detailed design)
   - [ ] V2_IMPLEMENTATION.md (code examples)

2. **Setup Environment**
   - [ ] Install Node.js 18+
   - [ ] Install Python 3.10+
   - [ ] Install PostgreSQL 15
   - [ ] Install Docker

3. **Create Project Structure**
   - [ ] Run: `mkdir crypto-signals-v2`
   - [ ] Create folders per architecture doc
   - [ ] Initialize git repo

4. **Start Phase 1**
   - [ ] Create PostgreSQL database
   - [ ] Set up API Gateway
   - [ ] Implement authentication

5. **Team Assignment**
   - [ ] Backend lead: Services & API
   - [ ] Frontend lead: Dashboards & theme
   - [ ] ML engineer: Models training
   - [ ] DevOps: Docker & deployment

---

## 📞 Common Questions

**Q: Will this conflict with existing code?**  
A: No - completely separate `crypto-signals-v2/` folder, nothing modified in existing code.

**Q: How confident should signals be before auto-trading?**  
A: Only execute on >80% confidence. Recommended 85%+ for real money.

**Q: What if a model gets 75% accuracy?**  
A: Only use for alerts, don't enable auto-trading. Retrain with more data.

**Q: How do I add new tokens to monitor?**  
A: Add to `SYMBOLS` config in admin dashboard. Signal engine automatically picks up.

**Q: Can I start trading immediately?**  
A: No - require 2 weeks backtesting + live paper trading first.

---

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Status:** Ready for implementation  

👉 **Next:** Read `V2_ARCHITECTURE.md` for detailed system design
