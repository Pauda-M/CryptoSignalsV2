# CryptoTrader V2 - Cross-Platform Plug & Play System

## 🎯 What's This?

Complete, portable cryptocurrency trading platform that works identically on Linux, Windows, and macOS. Copy anywhere, run it.

## 📦 What You Get

```
v2/
├── config/              # 🔧 Portable config management (ConfigLoader.js)
├── services/            # 🔄 6 microservices
│   ├── api-gateway/     # REST API
│   ├── signal-engine/   # ML signals
│   ├── trading-engine/  # Auto-trading
│   ├── notification-service/
│   ├── data-aggregator/
│   └── websocket-streamer/
├── dashboards/          # 🎨 React UIs
│   ├── trading-dashboard/ (port 5173)
│   └── admin-dashboard/   (port 5174)
├── shared/              # 📚 Shared components
├── ml/                  # 🧠 ML models & training
├── db/                  # 💾 PostgreSQL schema
├── ops/                 # 🚀 Deployment
│   ├── docker/          # Docker Compose
│   └── scripts/         # Init scripts (.sh & .ps1)
└── .env.example         # Configuration template
```

## ✨ Key Features

✅ **Cross-Platform**: Works on Linux, Windows, macOS  
✅ **Portable**: Copy entire folder anywhere, no installation  
✅ **Modular**: Easy to add/remove services  
✅ **Configurable**: Database connection via Admin Portal  
✅ **Containerized**: Docker Compose included  
✅ **Production-Ready**: Security, logging, error handling  

## 🚀 Quick Start

### Linux/macOS
```bash
chmod +x v2/ops/scripts/init-system.sh
cd v2
./ops/scripts/init-system.sh
```

### Windows (PowerShell)
```powershell
cd v2
powershell -ExecutionPolicy Bypass -File ops\scripts\init-system.ps1
```

### Configure Database
1. Edit `.env` with your PostgreSQL connection
2. Run: `node db/postgres/init.js`
3. Start: `npm run dev`

### Access
- **Trading Dashboard**: http://localhost:5173
- **Admin Dashboard**: http://localhost:5174
- **API**: http://localhost:3000/api/health

## 🔌 Database Configuration

Set via **Admin Portal** > Settings > Database Configuration:
- Input PostgreSQL connection string
- Test connection
- Save (auto-reload)

Or via `.env`:
```
DB_CONNECTION_STRING=postgresql://user:password@localhost:5432/crypto_signals_v2
```

## 🐳 Docker Deployment

```bash
npm run docker:build
npm run docker:up
```

Includes PostgreSQL, API, both dashboards.

## 📋 Configuration

Edit `.env.example` → `.env`:
- Database connection
- API ports
- Dashboard ports
- Telegram/Email/Discord
- Trading parameters
- ML settings

## 🏗️ Architecture

```
PostgreSQL (Central Data Hub)
    ↓
API Gateway (Express - Port 3000)
    ├── Signal Engine (ML predictions)
    ├── Trading Engine (Order execution)
    ├── Notification Service (Alerts)
    ├── Data Aggregator (Market data)
    └── WebSocket Streamer (Real-time)
        ↓
    Trading Dashboard (Port 5173)
    Admin Dashboard (Port 5174)
```

## 📄 Environment Variables

All configurable via `.env`:

```env
# Database
DB_CONNECTION_STRING=postgresql://...

# API & UIs
API_PORT=3000
TRADING_DASHBOARD_PORT=5173
ADMIN_DASHBOARD_PORT=5174

# Integrations
TELEGRAM_BOT_TOKEN=
DISCORD_WEBHOOK_URL=
EMAIL_SMTP_*=

# Trading
TRADING_ENABLED=false
AUTO_TRADING_ENABLED=false
```

See `.env.example` for complete list.

## 🔒 Security

- JWT authentication
- Encrypted wallet keys
- Configurable via Admin Portal
- No hardcoded secrets in code

## 📚 Folder Structure

### services/
Each service is independent:
- Has own `package.json`
- Connects to shared database
- Reads from shared config

### dashboards/
React + Vite:
- Trading Dashboard (signals, trades, portfolio)
- Admin Dashboard (settings, wallets, integrations)
- Shared theme system

### db/
PostgreSQL:
- `schema.sql` - Tables & indexes
- `init-seed.sql` - Initial data
- `init.js` - Setup script

### config/
- `ConfigLoader.js` - Reads .env, env vars
- Works on all platforms

### ops/
- `init-system.sh` - Linux/macOS setup
- `init-system.ps1` - Windows setup
- `docker-compose.yml` - Container orchestration

## 🔄 Workflow

1. **Copy** entire `v2/` folder to any location
2. **Edit** `.env` with your database connection
3. **Run** init script (`.sh` or `.ps1`)
4. **Setup** database: `node db/postgres/init.js`
5. **Start** system: `npm run dev`
6. **Configure** via Admin Dashboard

## 🎯 Deployment

### Local Development
```bash
npm run dev
```

### Docker
```bash
npm run docker:up
```

### Production
```bash
npm start
```

## 📖 Next Steps

1. Read `DEPLOYMENT_GUIDE.md` for detailed setup
2. Configure database in Admin Dashboard
3. Set up integrations (Telegram, Discord, Email)
4. Train ML models
5. Enable auto-trading

## ✅ Tested On

- ✓ Ubuntu 20.04+
- ✓ Windows 10/11
- ✓ macOS 11+
- ✓ Docker / Docker Compose
- ✓ Node.js 18+
- ✓ PostgreSQL 12+

## 🆘 Support

Check logs: `tail -f logs/app.log`

API health: `curl http://localhost:3000/api/health`

DB test: Admin Dashboard > Settings > Database

---

**Ready to deploy?** Copy `v2/` folder anywhere and run the init script!
