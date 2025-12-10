# CryptoTrader V2 - Deployment Guide

## Quick Start (Any OS)

### Prerequisites
- Node.js 18+
- Python 3.10+
- PostgreSQL 12+

### Setup (Linux/macOS)
```bash
chmod +x ops/scripts/init-system.sh
./ops/scripts/init-system.sh
```

### Setup (Windows PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File ops\scripts\init-system.ps1
```

### Configuration
1. Edit `.env` file with your settings
2. Set `DB_CONNECTION_STRING` to your PostgreSQL connection
3. Run database initialization:
   ```bash
   node db/postgres/init.js
   ```

### Start Services
```bash
npm run dev
```

### Access
- Trading Dashboard: http://localhost:5173
- Admin Dashboard: http://localhost:5174
- API Gateway: http://localhost:3000/api/health

## Docker Deployment

### Build
```bash
npm run docker:build
```

### Run
```bash
npm run docker:up
```

### Stop
```bash
npm run docker:down
```

## Database Connection

Connection string format:
```
postgresql://username:password@host:port/database
```

Set via:
1. `.env` file: `DB_CONNECTION_STRING`
2. Admin Dashboard: Settings > Database Configuration

## File Structure

```
v2/
├── config/              # Configuration management
├── services/            # Microservices
│   ├── api-gateway/
│   ├── signal-engine/
│   ├── trading-engine/
│   └── ...
├── dashboards/          # React UIs
│   ├── trading-dashboard/
│   └── admin-dashboard/
├── shared/              # Shared code
├── ml/                  # ML models
├── db/                  # Database
│   ├── postgres/        # SQL scripts
│   └── seeds/           # Initial data
├── ops/                 # Operations
│   ├── docker/
│   └── scripts/
└── .env.example         # Configuration template
```

## Portable Across Systems

This setup is designed to work identically on:
- Linux (Ubuntu, Debian, CentOS)
- Windows (10+)
- macOS

Simply copy the entire `v2/` folder and run initialization scripts.

## Admin Portal - Database Configuration

After startup, access Admin Dashboard:
1. Go to http://localhost:5174
2. Navigate to: Settings > Database Configuration
3. Enter PostgreSQL connection string
4. Click "Test Connection"
5. Click "Save Configuration"

The system will reload with the new database connection.
