# CryptoTrader V2 - Modular Architecture

**Status:** Planning & Setup Guide  
**Goal:** Build completely independent, modular system alongside existing codebase  
**Approach:** Non-breaking, can integrate with legacy system later if needed

## New Folder Structure

```
crypto-signals-v2/                          ← NEW INDEPENDENT SYSTEM
│
├── 📁 services/                            ← Microservices
│   ├── signal-engine/                      ← ML signal generation
│   │   ├── src/
│   │   │   ├── models/                     ← ML models (80-85% confidence target)
│   │   │   │   ├── predictive.py
│   │   │   │   ├── alpha.py
│   │   │   │   ├── ensemble.py
│   │   │   │   └── backtest.py
│   │   │   ├── features/
│   │   │   │   ├── technical.py
│   │   │   │   ├── sentiment.py
│   │   │   │   └── onchain.py
│   │   │   ├── ingestion/
│   │   │   │   ├── binance.py
│   │   │   │   ├── pumpfun.py
│   │   │   │   └── dex.py
│   │   │   ├── engine.py                   ← Main signal processor
│   │   │   └── config.yaml
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── README.md
│   │
│   ├── trading-engine/                     ← Auto-trading execution
│   │   ├── src/
│   │   │   ├── executor.py                 ← Execute trades
│   │   │   ├── portfolio.py                ← Track positions
│   │   │   ├── risk.py                     ← Risk management
│   │   │   ├── wallet.py                   ← Wallet management
│   │   │   └── config.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── api-gateway/                        ← REST API + GraphQL
│   │   ├── src/
│   │   │   ├── server.js
│   │   │   ├── routes/
│   │   │   │   ├── signals.js
│   │   │   │   ├── trading.js
│   │   │   │   ├── portfolio.js
│   │   │   │   ├── admin.js
│   │   │   │   └── integrations.js
│   │   │   ├── middleware/
│   │   │   │   ├── auth.js
│   │   │   │   └── validation.js
│   │   │   └── config.js
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── notification-service/               ← Telegram, Email, Webhook
│   │   ├── src/
│   │   │   ├── telegram.js
│   │   │   ├── email.js
│   │   │   ├── webhook.js
│   │   │   └── dispatcher.py
│   │   ├── requirements.txt
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── data-aggregator/                    ← Data ingestion & normalization
│   │   ├── src/
│   │   │   ├── normalizer.py
│   │   │   ├── cache.py
│   │   │   └── scheduler.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── websocket-streamer/                 ← Real-time updates
│       ├── src/
│       │   ├── server.js
│       │   └── handlers.js
│       ├── package.json
│       └── Dockerfile
│
├── 📁 dashboards/                          ← Frontend Applications
│   ├── trading-dashboard/                  ← Trader UI
│   │   ├── src/
│   │   │   ├── App.jsx
│   │   │   ├── components/
│   │   │   │   ├── SignalBoard.jsx
│   │   │   │   ├── Portfolio.jsx
│   │   │   │   ├── OrderBook.jsx
│   │   │   │   ├── Charts.jsx
│   │   │   │   └── Alerts.jsx
│   │   │   ├── pages/
│   │   │   │   ├── Dashboard.jsx
│   │   │   │   ├── Signals.jsx
│   │   │   │   ├── Trading.jsx
│   │   │   │   └── Analytics.jsx
│   │   │   ├── services/
│   │   │   │   ├── api.js
│   │   │   │   ├── websocket.js
│   │   │   │   └── auth.js
│   │   │   ├── hooks/
│   │   │   ├── utils/
│   │   │   ├── theme/
│   │   │   │   └── theme.js                ← SHARED THEME
│   │   │   └── main.jsx
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   ├── tailwind.config.js
│   │   └── Dockerfile
│   │
│   └── admin-dashboard/                    ← Admin/Configuration UI
│       ├── src/
│       │   ├── App.jsx
│       │   ├── components/
│       │   │   ├── SettingsPanel.jsx
│       │   │   ├── ModelManagement.jsx
│       │   │   ├── WalletManager.jsx
│       │   │   ├── IntegrationConfig.jsx
│       │   │   ├── UserManagement.jsx
│       │   │   └── Analytics.jsx
│       │   ├── pages/
│       │   │   ├── Dashboard.jsx
│       │   │   ├── Settings.jsx
│       │   │   ├── Integrations.jsx
│       │   │   ├── Wallets.jsx
│       │   │   ├── Models.jsx
│       │   │   └── Monitoring.jsx
│       │   ├── services/
│       │   │   ├── api.js
│       │   │   └── auth.js
│       │   ├── theme/
│       │   │   └── theme.js                ← SHARED THEME
│       │   └── main.jsx
│       ├── package.json
│       ├── vite.config.js
│       ├── tailwind.config.js
│       └── Dockerfile
│
├── 📁 shared/                              ← Reusable code
│   ├── ui-components/
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   ├── Chart.jsx
│   │   ├── Table.jsx
│   │   ├── Modal.jsx
│   │   └── ...
│   ├── types/
│   │   ├── signals.ts
│   │   ├── trading.ts
│   │   └── config.ts
│   ├── utils/
│   │   ├── api-client.js
│   │   ├── validators.js
│   │   ├── formatters.js
│   │   └── constants.js
│   └── theme/
│       ├── colors.js
│       ├── typography.js
│       ├── spacing.js
│       └── index.js
│
├── 📁 db/                                  ← Database layer
│   ├── postgres/
│   │   ├── schema.sql
│   │   ├── migrations/
│   │   │   ├── 001_init.sql
│   │   │   ├── 002_signals.sql
│   │   │   ├── 003_trading.sql
│   │   │   ├── 004_wallets.sql
│   │   │   └── 005_integrations.sql
│   │   └── seeds/
│   │       ├── models.sql
│   │       └── default-config.sql
│   ├── models/
│   │   ├── signal.js
│   │   ├── trade.js
│   │   ├── wallet.js
│   │   ├── user.js
│   │   └── integration.js
│   └── connection.js
│
├── 📁 ops/                                 ← Operations
│   ├── docker-compose.yml                  ← All services
│   ├── kubernetes/
│   │   ├── deployments/
│   │   ├── services/
│   │   └── configmaps/
│   ├── scripts/
│   │   ├── setup.sh
│   │   ├── migrate.sh
│   │   ├── backup.sh
│   │   └── restore.sh
│   ├── monitoring/
│   │   ├── prometheus.yml
│   │   ├── grafana/
│   │   └── alerts.yml
│   └── logs/
│
├── 📁 ml/                                  ← Machine Learning
│   ├── models/
│   │   ├── predictive/
│   │   │   ├── train.py                    ← 80-85% target
│   │   │   ├── evaluate.py
│   │   │   ├── predict.py
│   │   │   └── saved_models/
│   │   ├── alpha/
│   │   │   ├── train.py
│   │   │   ├── features/
│   │   │   └── saved_models/
│   │   └── ensemble/
│   │       ├── combiner.py
│   │       └── configs/
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │   └── features/
│   ├── notebooks/
│   │   ├── exploration.ipynb
│   │   ├── training.ipynb
│   │   └── evaluation.ipynb
│   ├── requirements.txt
│   ├── config.yaml
│   └── README.md
│
├── 📁 tests/                               ← Testing
│   ├── unit/
│   │   ├── signal-engine/
│   │   ├── trading-engine/
│   │   └── api/
│   ├── integration/
│   ├── e2e/
│   └── performance/
│
├── 📁 docs/                                ← Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── SETUP.md
│   ├── DEPLOYMENT.md
│   ├── ML-MODELS.md
│   ├── INTEGRATIONS.md
│   ├── TRADING.md
│   ├── ADMIN-GUIDE.md
│   └── DEVELOPER.md
│
├── .env.example
├── docker-compose.yml                      ← Master compose
├── ecosystem.config.js                     ← PM2 config (optional)
├── package.json                            ← Root workspace (Node services)
├── pyproject.toml                          ← Root Python project
├── Makefile
├── README.md
└── .gitignore
```

## Database Schema (Core Tables)

```sql
-- Users & Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    role ENUM('ADMIN', 'TRADER', 'VIEWER'),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Wallet Management
CREATE TABLE wallets (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    exchange VARCHAR(50),  -- 'binance', 'kucoin', 'dex'
    address VARCHAR(255),
    private_key_encrypted TEXT,
    balance_btc DECIMAL,
    balance_usd DECIMAL,
    is_active BOOLEAN,
    created_at TIMESTAMP
);

-- Signals (Core Predictions + Alpha)
CREATE TABLE signals (
    id UUID PRIMARY KEY,
    symbol VARCHAR(50),
    signal_type ENUM('CORE', 'ALPHA'),  -- Predictive vs Opportunity
    direction ENUM('BUY', 'SELL', 'HOLD'),
    confidence DECIMAL(5,4),  -- Target: 0.80-0.85
    entry_price DECIMAL(18,8),
    stop_loss DECIMAL(18,8),
    take_profit DECIMAL(18,8),
    market_trend VARCHAR(50),
    social_heat DECIMAL(5,4),
    dex_behavior DECIMAL(5,4),
    ml_model_version VARCHAR(50),
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    INDEX(symbol, created_at)
);

-- Active Trades (Auto-Trading)
CREATE TABLE trades (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    wallet_id UUID REFERENCES wallets(id),
    signal_id UUID REFERENCES signals(id),
    symbol VARCHAR(50),
    side ENUM('BUY', 'SELL'),
    quantity DECIMAL(18,8),
    entry_price DECIMAL(18,8),
    current_price DECIMAL(18,8),
    stop_loss DECIMAL(18,8),
    take_profit DECIMAL(18,8),
    status ENUM('PENDING', 'OPEN', 'CLOSED', 'STOPPED'),
    pnl DECIMAL(18,8),
    pnl_percent DECIMAL(10,4),
    created_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- Portfolio Performance
CREATE TABLE portfolios (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    total_value_btc DECIMAL(18,8),
    total_value_usd DECIMAL(18,8),
    today_pnl_percent DECIMAL(10,4),
    total_pnl_percent DECIMAL(10,4),
    win_rate DECIMAL(5,4),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Integrations (Telegram, Webhook, etc)
CREATE TABLE integrations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    type ENUM('TELEGRAM', 'EMAIL', 'WEBHOOK', 'DISCORD'),
    config JSONB,  -- chatID, token, URL, etc
    is_active BOOLEAN,
    created_at TIMESTAMP
);

-- ML Model Versions
CREATE TABLE ml_models (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    type ENUM('PREDICTIVE', 'ALPHA', 'ENSEMBLE'),
    version VARCHAR(20),
    accuracy DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    is_active BOOLEAN,
    model_path VARCHAR(255),
    created_at TIMESTAMP,
    trained_at TIMESTAMP
);

-- Configuration Parameters
CREATE TABLE config (
    id UUID PRIMARY KEY,
    key VARCHAR(100) UNIQUE,
    value JSONB,
    description TEXT,
    updated_at TIMESTAMP
);
```

## Key Features by Component

### Signal Engine (Python)
```
✓ ML Models: Predictive (80-85% target) + Alpha
✓ Features: Technical + Sentiment + On-chain
✓ Input: Binance OHLC, PumpFun, DEX data
✓ Output: Signals with confidence scores
✓ Backtesting: Historical validation
```

### Trading Engine (Python)
```
✓ Wallet Management: Multi-exchange support
✓ Auto-Trading: Execute on signal triggers
✓ Risk Management: SL/TP, position sizing
✓ Portfolio Tracking: Real-time PnL
✓ Slippage Handling: DEX-specific logic
```

### API Gateway (Node.js)
```
✓ REST API: /api/signals, /api/trading, /api/admin
✓ Authentication: JWT tokens
✓ Rate limiting & validation
✓ WebSocket support for real-time
```

### Trading Dashboard (React)
```
✓ Signal Board: Live signals with confidence
✓ Portfolio: Holdings, PnL, performance
✓ Order Book: Active positions
✓ Charts: TradingView-style candlesticks
✓ Alerts: Real-time notifications
✓ Analytics: Win rate, Sharpe ratio, etc
```

### Admin Dashboard (React)
```
✓ Settings: Risk parameters, model config
✓ Wallet Manager: Add/edit wallets (encrypted storage)
✓ Integrations: Telegram (chatID, token), Webhooks, Email
✓ Model Management: Upload, versions, activate
✓ User Management: Roles, permissions
✓ Monitoring: System health, service status
✓ Logs: Activity audit trail
```

## Shared Theme System

```javascript
// shared/theme/index.js
export const theme = {
  colors: {
    primary: '#0066CC',
    success: '#00CC33',
    danger: '#FF3333',
    warning: '#FFAA00',
    dark: '#1A1A1A',
    light: '#F5F5F5',
  },
  typography: {
    // Unified fonts
  },
  spacing: {
    // Unified spacing scale
  },
  components: {
    // Buttons, Cards, etc - same across both dashboards
  }
};
```

## ML Model Strategy (80-85% Confidence)

### Predictive Model
```python
# 1. Features (from technical + market data)
- Price momentum (1h, 4h, 1d)
- RSI, MACD, Bollinger Bands
- Volume profile
- Support/Resistance levels
- Moving average crossovers

# 2. Ensemble approach
- XGBoost for classification
- LightGBM for secondary validation
- Voting mechanism for final signal

# 3. Target metrics
- Accuracy: 80-85%
- Precision: >80% (reduce false positives)
- Recall: >75% (don't miss opportunities)
- F1-Score: >0.77

# 4. Backtesting
- Historical validation: 2 years
- Walk-forward analysis
- Monte Carlo simulation
- Max drawdown limits
```

### Alpha Model
```python
# 1. Multi-source scoring
- Market trend strength: 30%
- Social heat (sentiment): 30%
- DEX behavior (on-chain): 25%
- Anomaly detection: 15%

# 2. Target: Identify 100X opportunities
- Early detection (first 24h)
- Community size & growth
- Whale movement patterns
- Unusual trading volume

# 3. Confidence requirement
- Min 0.80 alpha_score for alert
- All components > 0.65 threshold
```

## Modular Service Integration

### Adding New Service (Example: RiskManager)
```
1. Create: services/risk-manager/
2. API endpoint: /api/risk/analyze
3. Connect to: Trading Engine via message queue
4. Database: Uses shared crypto_signals_v2 DB
5. Docker: Included in docker-compose.yml
6. Theme: Inherits shared theme if has UI
```

### Adding New Dashboard (Example: VolumeAnalyzer)
```
1. Create: dashboards/volume-analyzer/
2. Use shared components: Button, Card, Chart
3. Connect to: API Gateway for data
4. Theme: Automatically uses shared theme
5. Build: npm run build (part of monorepo)
```

## Integration Configuration Examples

```yaml
# admin-dashboard/integrations

Telegram:
  chat_id: "123456789"
  bot_token: "BOT_TOKEN_HERE"
  
Email:
  smtp_server: "smtp.gmail.com"
  sender_email: "alerts@example.com"
  
Webhook:
  url: "https://webhook.site/xxxxx"
  
Discord:
  webhook_url: "https://discord.com/api/webhooks/xxxxx"
```

## Getting Started

```bash
# Clone/setup
git clone <repo>
cd crypto-signals-v2

# Install all
make install

# Setup environment
cp .env.example .env
# Edit .env with your settings

# Run database migrations
make db-migrate

# Start all services (Docker Compose)
docker-compose up -d

# Or run locally with PM2
pm2 start ecosystem.config.js

# Check status
pm2 status

# View logs
pm2 logs
```

## Next Steps

1. **Database**: Create PostgreSQL with schema
2. **Services**: Implement API Gateway first (connects everything)
3. **Dashboards**: Build Admin Dashboard (configure system)
4. **ML Models**: Train Predictive model (80-85% target)
5. **Trading**: Implement auto-trading (small positions first)
6. **Integration**: Connect Telegram, webhooks for alerts

---

**Status:** Ready for implementation  
**Independent from:** Existing codebase (no conflicts)  
**Modular:** Easy to add/remove services  
**Scalable:** Docker/Kubernetes ready  
**Target:** Production-ready by Q1 2026
