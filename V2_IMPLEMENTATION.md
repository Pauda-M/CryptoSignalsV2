# CryptoTrader V2 - Implementation Roadmap

## Phase 1: Foundation (Weeks 1-2)

### 1.1 Database Setup
```bash
# Create new PostgreSQL database
createdb crypto_signals_v2

# Run schema migrations
psql crypto_signals_v2 < db/postgres/schema.sql
psql crypto_signals_v2 < db/postgres/migrations/001_init.sql
psql crypto_signals_v2 < db/postgres/migrations/002_signals.sql
# ... etc
```

**Files to create:**
- `db/postgres/schema.sql` - Complete schema with all tables
- `db/postgres/migrations/*.sql` - Incremental migrations
- `db/connection.js` - Connection pool

### 1.2 API Gateway (Node.js)
**Priority:** HIGH - Everything connects to this

```bash
cd services/api-gateway
npm init -y
npm install express pg dotenv cors helmet
npm install jsonwebtoken bcryptjs
npm install socket.io
```

**Core files:**
- `src/server.js` - Express app, middleware setup
- `src/routes/signals.js` - GET signals, POST subscribe
- `src/routes/trading.js` - GET trades, POST execute
- `src/routes/admin.js` - Settings, model config
- `src/middleware/auth.js` - JWT validation
- `db/connection.js` - PostgreSQL pool

**Key endpoints:**
```
GET    /api/health
POST   /api/auth/login
POST   /api/auth/refresh

GET    /api/signals/latest
GET    /api/signals/:id
POST   /api/signals/subscribe

GET    /api/trading/positions
GET    /api/trading/history
POST   /api/trading/execute

GET    /api/admin/config
POST   /api/admin/config
POST   /api/admin/wallets
POST   /api/admin/integrations

WS     /ws/updates
```

### 1.3 Basic Shared Theme
```javascript
// shared/theme/index.js
export const darkTheme = {
  colors: {
    primary: '#0066CC',
    secondary: '#6B21A8',
    success: '#10B981',
    danger: '#EF4444',
    warning: '#F59E0B',
    dark: '#1F2937',
    light: '#F9FAFB',
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
  }
};
```

---

## Phase 2: Core Dashboards (Weeks 3-4)

### 2.1 Trading Dashboard (React)

**Setup:**
```bash
cd dashboards/trading-dashboard
npm create vite@latest . -- --template react
npm install
npm install axios zustand react-chartjs-2 chart.js
npm install react-router-dom
npm install tailwindcss postcss autoprefixer
npm install socket.io-client
```

**Key pages:**
```
/dashboard          → Overview, portfolio stats
/signals            → Live signals board
/trading            → Active positions, order history
/portfolio          → Holdings, performance charts
/analytics          → Win rate, Sharpe, drawdown
```

**Components:**
```jsx
// src/components/SignalBoard.jsx
- Real-time signal list
- Confidence score color-coded
- One-click subscribe/trading buttons

// src/components/Portfolio.jsx
- Total balance (BTC/USD)
- Open positions with PnL
- Closed trades history

// src/components/Charts.jsx
- TradingView-like candlesticks
- Volume profile
- Technical indicators overlay
```

### 2.2 Admin Dashboard (React)

**Setup:** Same as trading dashboard

**Key pages:**
```
/settings           → Risk parameters, model config
/wallets            → Add/manage wallets (encrypted)
/integrations       → Telegram, Email, Webhook setup
/models             → Upload, version, activate ML models
/users              → Create accounts, assign roles
/monitoring         → Service health, logs
```

**Components:**
```jsx
// src/components/WalletManager.jsx
- Add wallet (Exchange API key + secret - encrypted)
- Test connection
- View balance

// src/components/IntegrationConfig.jsx
- Telegram bot setup (chatID, token)
- Email alerts configuration
- Webhook URL registration
- Discord webhook

// src/components/ModelManager.jsx
- Upload .pkl or .pt model files
- Version history
- Accuracy metrics display
- Activate/deactivate models
```

---

## Phase 3: ML Model Development (Weeks 5-6)

### 3.1 Predictive Model (80-85% Target)

**File structure:**
```
ml/models/predictive/
├── train.py           ← Main training script
├── evaluate.py        ← Validation & metrics
├── predict.py         ← Inference
├── features.py        ← Feature engineering
├── requirements.txt
└── saved_models/
    ├── model_v1.pkl
    ├── scaler_v1.pkl
    └── metadata_v1.json
```

**Sample training code:**
```python
# ml/models/predictive/train.py
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pickle

class PredictiveModel:
    def __init__(self):
        self.models = {
            'xgb': xgb.XGBClassifier(n_estimators=200, max_depth=8, learning_rate=0.05),
            'lgb': lgb.LGBMClassifier(n_estimators=200, max_depth=8),
        }
        self.scaler = StandardScaler()
        self.meta_model = GradientBoostingClassifier()
    
    def prepare_features(self, df):
        """Calculate technical features"""
        df['rsi'] = self._calculate_rsi(df['close'])
        df['macd'] = self._calculate_macd(df['close'])
        df['bb_upper'], df['bb_lower'] = self._bollinger_bands(df['close'])
        df['momentum'] = df['close'].pct_change()
        df['volume_sma'] = df['volume'].rolling(20).mean()
        return df
    
    def train(self, X, y):
        """Train ensemble model"""
        X_scaled = self.scaler.fit_transform(X)
        
        # Train base models
        for name, model in self.models.items():
            model.fit(X_scaled, y)
        
        # Meta-learner on base predictions
        meta_features = np.column_stack([
            model.predict_proba(X_scaled)[:, 1] 
            for model in self.models.values()
        ])
        self.meta_model.fit(meta_features, y)
        
        return self
    
    def predict(self, X):
        """Get prediction with confidence"""
        X_scaled = self.scaler.transform(X)
        meta_features = np.column_stack([
            model.predict_proba(X_scaled)[:, 1] 
            for model in self.models.values()
        ])
        confidence = self.meta_model.predict_proba(meta_features)[:, 1]
        direction = self.meta_model.predict(meta_features)
        return direction, confidence
    
    def save(self, path):
        """Save model to disk"""
        with open(f'{path}/model.pkl', 'wb') as f:
            pickle.dump(self, f)
    
    @staticmethod
    def load(path):
        """Load model from disk"""
        with open(f'{path}/model.pkl', 'rb') as f:
            return pickle.load(f)

# Training
if __name__ == "__main__":
    # Load data (2 years historical)
    df = pd.read_csv('data/historical.csv')
    
    # Prepare features
    model = PredictiveModel()
    df = model.prepare_features(df)
    
    X = df[['rsi', 'macd', 'momentum', ...]]
    y = df['next_direction']  # 1=UP, 0=DOWN
    
    # Split (80/20)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    # Train
    model.train(X_train, y_train)
    
    # Evaluate
    y_pred, conf = model.predict(X_test)
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.2%}")
    print(f"Precision: {precision_score(y_test, y_pred):.2%}")
    print(f"Recall: {recall_score(y_test, y_pred):.2%}")
    print(f"F1: {f1_score(y_test, y_pred):.2f}")
    
    # Save
    model.save('saved_models/')
```

### 3.2 Alpha Model (100X Spotting)

**File structure:**
```
ml/models/alpha/
├── train.py
├── features.py
├── scoring.py
├── requirements.txt
└── saved_models/
```

**Sample code:**
```python
# ml/models/alpha/scoring.py
class AlphaScorer:
    def __init__(self):
        self.weights = {
            'market_trend': 0.30,
            'social_heat': 0.30,
            'dex_behavior': 0.25,
            'anomaly': 0.15,
        }
    
    def score(self, symbol):
        """Calculate alpha score for emerging token"""
        scores = {
            'market_trend': self._analyze_trend(symbol),
            'social_heat': self._analyze_sentiment(symbol),
            'dex_behavior': self._analyze_onchain(symbol),
            'anomaly': self._detect_anomaly(symbol),
        }
        
        alpha_score = sum(
            scores[k] * self.weights[k] 
            for k in scores.keys()
        )
        
        return {
            'alpha_score': alpha_score,
            'components': scores,
            'recommendation': 'BUY' if alpha_score > 0.80 else 'HOLD'
        }
    
    def _analyze_trend(self, symbol):
        """Technical pattern analysis"""
        # Check for breakout, continuation, reversal patterns
        pass
    
    def _analyze_sentiment(self, symbol):
        """Twitter/Discord sentiment"""
        # Mentions, engagement, trending keywords
        pass
    
    def _analyze_onchain(self, symbol):
        """On-chain metrics"""
        # Whale movements, liquidity, volume profile
        pass
    
    def _detect_anomaly(self, symbol):
        """Unusual trading patterns"""
        # Coordinated activity, pump/dump signature
        pass
```

---

## Phase 4: Signal Engine (Week 7)

**File: services/signal-engine/src/engine.py**

```python
import asyncio
import psycopg2
from datetime import datetime, timedelta
from ml.models.predictive.train import PredictiveModel
from ml.models.alpha.scoring import AlphaScorer

class SignalEngine:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)
        self.predictive_model = PredictiveModel.load('ml/models/predictive/saved_models/')
        self.alpha_scorer = AlphaScorer()
    
    async def generate_signals_loop(self):
        """Main signal generation loop"""
        while True:
            try:
                await self.generate_core_signals()  # 80-85% confidence
                await self.generate_alpha_signals()  # 100X spotting
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                print(f"[SignalEngine] Error: {e}")
                await asyncio.sleep(10)
    
    async def generate_core_signals(self):
        """ML-based predictions (BUY/SELL/HOLD)"""
        assets = self._get_active_assets()
        
        for asset in assets:
            try:
                # Fetch OHLC data
                ohlc = self._fetch_ohlc(asset, '1h', 200)
                
                # Prepare features
                features = self._prepare_features(ohlc)
                
                # Predict
                direction, confidence = self.predictive_model.predict(features[-1:])
                
                # Only store high-confidence signals (>80%)
                if confidence[0] > 0.80:
                    signal = {
                        'symbol': asset,
                        'signal_type': 'CORE',
                        'direction': 'BUY' if direction[0] else 'SELL',
                        'confidence': float(confidence[0]),
                        'entry_price': ohlc['close'].iloc[-1],
                        'stop_loss': self._calculate_sl(ohlc),
                        'take_profit': self._calculate_tp(ohlc),
                        'ml_model_version': 'predictive_v1',
                        'created_at': datetime.now(),
                    }
                    self._store_signal(signal)
                    print(f"[Signal] {asset} {direction} @ {confidence[0]:.2%}")
            
            except Exception as e:
                print(f"[Error] {asset}: {e}")
    
    async def generate_alpha_signals(self):
        """Spot 100X opportunities"""
        candidates = self._get_emerging_tokens()
        
        for token in candidates:
            try:
                result = self.alpha_scorer.score(token)
                
                if result['alpha_score'] > 0.80:
                    signal = {
                        'symbol': token['symbol'],
                        'signal_type': 'ALPHA',
                        'direction': '100X_ALERT',
                        'alpha_components': result['components'],
                        'overall_alpha_score': result['alpha_score'],
                        'created_at': datetime.now(),
                    }
                    self._store_signal(signal)
                    print(f"[Alpha] {token['symbol']} {result['alpha_score']:.2%}")
            
            except Exception as e:
                print(f"[Error] {token}: {e}")
    
    def _store_signal(self, signal):
        """Insert signal into DB"""
        query = """
        INSERT INTO signals 
        (symbol, signal_type, direction, confidence, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (
                signal['symbol'],
                signal['signal_type'],
                signal['direction'],
                signal.get('confidence', 0),
                signal['created_at'],
            ))
        self.conn.commit()

if __name__ == "__main__":
    engine = SignalEngine({
        'host': 'localhost',
        'database': 'crypto_signals_v2',
        'user': 'postgres',
        'password': 'password',
    })
    asyncio.run(engine.generate_signals_loop())
```

---

## Phase 5: Trading Engine & Auto-Trading (Week 8)

**File: services/trading-engine/src/executor.py**

```python
class AutoTrader:
    def __init__(self, wallet_config):
        self.wallet = WalletManager(wallet_config)
        self.exchange = BinanceExchange(wallet_config)
    
    async def execute_on_signal(self, signal):
        """Auto-trade when signal confidence > 80%"""
        
        if signal['confidence'] < 0.80:
            print(f"[AutoTrader] Skip - confidence too low")
            return
        
        try:
            # Size calculation
            quantity = self._calculate_position_size(signal)
            
            # Place order
            order = self.exchange.create_order(
                symbol=signal['symbol'],
                side=signal['direction'],
                quantity=quantity,
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
            )
            
            # Store trade record
            self._store_trade(signal, order)
            
            # Send notification
            await notify_user(f"Opened {order['id']}: {signal}")
            
        except Exception as e:
            print(f"[Error] Trade execution failed: {e}")
    
    def _calculate_position_size(self, signal):
        """Risk-based position sizing"""
        account_value = self.wallet.get_total_value()
        risk_per_trade = 0.02  # 2% per trade
        risk_amount = account_value * risk_per_trade
        
        price_diff = abs(signal['entry_price'] - signal['stop_loss'])
        quantity = risk_amount / price_diff
        
        return quantity
```

---

## Phase 6: Integration & Testing (Week 9)

### 6.1 Telegram Integration
```python
# services/notification-service/src/telegram.py
import requests

class TelegramNotifier:
    def __init__(self, chat_id, bot_token):
        self.chat_id = chat_id
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_signal(self, signal):
        """Send signal to Telegram"""
        message = f"""
🎯 NEW SIGNAL
Symbol: {signal['symbol']}
Direction: {signal['direction']}
Confidence: {signal['confidence']:.0%}
Entry: {signal['entry_price']}
SL: {signal['stop_loss']}
TP: {signal['take_profit']}
        """
        requests.post(
            f"{self.api_url}/sendMessage",
            json={"chat_id": self.chat_id, "text": message}
        )
```

### 6.2 Admin Integration Config
```jsx
// dashboards/admin-dashboard/src/components/IntegrationConfig.jsx
function TelegramSetup() {
  const [chatId, setChatId] = useState('');
  const [botToken, setBotToken] = useState('');
  
  const handleSave = async () => {
    await api.post('/api/admin/integrations', {
      type: 'TELEGRAM',
      config: { chat_id: chatId, bot_token: botToken }
    });
  };
  
  return (
    <div>
      <h3>Telegram Configuration</h3>
      <input 
        placeholder="Chat ID" 
        value={chatId} 
        onChange={e => setChatId(e.target.value)}
      />
      <input 
        placeholder="Bot Token" 
        value={botToken} 
        onChange={e => setBotToken(e.target.value)}
        type="password"
      />
      <button onClick={handleSave}>Save</button>
    </div>
  );
}
```

---

## Deployment

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: crypto_signals_v2
      POSTGRES_PASSWORD: password
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  api-gateway:
    build: ./services/api-gateway
    ports:
      - "3000:3000"
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://postgres:password@postgres:5432/crypto_signals_v2

  signal-engine:
    build: ./services/signal-engine
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://postgres:password@postgres:5432/crypto_signals_v2

  trading-engine:
    build: ./services/trading-engine
    depends_on:
      - postgres
      - api-gateway

  trading-dashboard:
    build: ./dashboards/trading-dashboard
    ports:
      - "5173:5173"

  admin-dashboard:
    build: ./dashboards/admin-dashboard
    ports:
      - "5174:5173"

  notification-service:
    build: ./services/notification-service
    depends_on:
      - postgres

volumes:
  pgdata:
```

---

## Testing Strategy

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Load testing
locust -f tests/performance/locustfile.py

# Model evaluation
python ml/models/predictive/evaluate.py
```

---

**Timeline:** 9 weeks total  
**Status:** Ready for implementation  
**Independent:** Completely separate from existing codebase  
**Modular:** Can add/remove services easily  
**Scalable:** Docker/Kubernetes ready
