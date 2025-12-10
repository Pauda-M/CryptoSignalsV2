-- Initial seed data for CryptoTrader V2
-- Executed after schema creation

INSERT INTO users (email, username, password_hash, is_admin, is_active) VALUES
('postgres@cryptotrader.local', 'postgres', '$2b$10$..hash..', true, true),
('user@cryptotrader.local', 'user', '$2b$10$..hash..', false, true)
ON CONFLICT (email) DO NOTHING;

INSERT INTO assets (symbol, name, exchange, is_active) VALUES
('BTCUSDT', 'Bitcoin', 'binance', true),
('ETHUSDT', 'Ethereum', 'binance', true),
('BNBUSDT', 'Binance Coin', 'binance', true),
('XRPUSDT', 'Ripple', 'binance', true),
('ADAUSDT', 'Cardano', 'binance', true)
ON CONFLICT (symbol) DO NOTHING;

INSERT INTO system_config (config_key, config_value) VALUES
('system_initialized', 'true'),
('system_version', '2.0.0'),
('last_migration', NOW()::text)
ON CONFLICT (config_key) DO UPDATE SET config_value = EXCLUDED.config_value;
