/**
 * ConfigLoader.js - Cross-platform configuration management
 * Reads from environment variables and .env file
 * Works on Linux and Windows
 * 
 * Usage:
 *   const config = require('./ConfigLoader');
 *   console.log(config.database.connectionString);
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

class ConfigLoader {
    constructor() {
        this.isDevelopment = (process.env.NODE_ENV || 'development') === 'development';
        this.isWindows = os.platform() === 'win32';
        this.isLinux = os.platform() === 'linux';
        this.config = {};
        this.errors = [];
        
        this.load();
    }

    /**
     * Load configuration from .env and environment variables
     */
    load() {
        this.loadEnvFile();
        this.parseConfig();
        this.validateRequired();
    }

    /**
     * Load .env file if it exists (Linux/Windows compatible)
     */
    loadEnvFile() {
        const envPath = path.join(process.cwd(), '.env');
        
        if (fs.existsSync(envPath)) {
            const envContent = fs.readFileSync(envPath, 'utf8');
            envContent.split('\n').forEach(line => {
                const trimmed = line.trim();
                if (!trimmed || trimmed.startsWith('#')) return;
                
                const [key, ...valueParts] = trimmed.split('=');
                const value = valueParts.join('=').trim();
                
                // Remove quotes if present (handles both ' and ")
                const cleanValue = value
                    .replace(/^["']|["']$/g, '')
                    .replace(/\\n/g, '\n');
                
                if (key && !process.env[key]) {
                    process.env[key] = cleanValue;
                }
            });
        }
    }

    /**
     * Parse all configuration from environment
     */
    parseConfig() {
        this.config = {
            // ========== DATABASE ==========
            database: {
                connectionString: this.getEnv('DB_CONNECTION_STRING', null),
                host: this.getEnv('DB_HOST', 'localhost'),
                port: parseInt(this.getEnv('DB_PORT', '5432')),
                user: this.getEnv('DB_USER', 'postgres'),
                password: this.getEnv('DB_PASSWORD', 'KarmaKoma2024'),
                database: this.getEnv('DB_NAME', 'crypto_signals_v2'),
            },

            // ========== API GATEWAY ==========
            api: {
                port: parseInt(this.getEnv('API_PORT', '3000')),
                host: this.getEnv('API_HOST', '0.0.0.0'),
                env: this.getEnv('NODE_ENV', 'development'),
            },

            // ========== DASHBOARDS ==========
            dashboards: {
                trading: {
                    port: parseInt(this.getEnv('TRADING_DASHBOARD_PORT', '5173')),
                    url: this.getEnv('TRADING_DASHBOARD_URL', null),
                },
                admin: {
                    port: parseInt(this.getEnv('ADMIN_DASHBOARD_PORT', '5174')),
                    url: this.getEnv('ADMIN_DASHBOARD_URL', null),
                },
            },

            // ========== WEBSOCKET ==========
            websocket: {
                port: parseInt(this.getEnv('WEBSOCKET_PORT', '4101')),
                host: this.getEnv('WEBSOCKET_HOST', '0.0.0.0'),
            },

            // ========== ML/MODELS ==========
            ml: {
                port: parseInt(this.getEnv('ML_PORT', '5000')),
                updateInterval: parseInt(this.getEnv('MODEL_UPDATE_INTERVAL', '300000')),
            },

            // ========== NOTIFICATIONS ==========
            notifications: {
                telegram: {
                    botToken: this.getEnv('TELEGRAM_BOT_TOKEN', ''),
                    chatId: this.getEnv('TELEGRAM_CHAT_ID', ''),
                    enabled: !!this.getEnv('TELEGRAM_BOT_TOKEN', ''),
                },
                email: {
                    smtpHost: this.getEnv('EMAIL_SMTP_HOST', ''),
                    smtpPort: parseInt(this.getEnv('EMAIL_SMTP_PORT', '587')),
                    user: this.getEnv('EMAIL_SMTP_USER', ''),
                    password: this.getEnv('EMAIL_SMTP_PASSWORD', ''),
                    from: this.getEnv('EMAIL_FROM', ''),
                    enabled: !!this.getEnv('EMAIL_SMTP_USER', ''),
                },
            },

            // ========== INTEGRATIONS ==========
            integrations: {
                discord: {
                    webhookUrl: this.getEnv('DISCORD_WEBHOOK_URL', ''),
                    enabled: !!this.getEnv('DISCORD_WEBHOOK_URL', ''),
                },
                slack: {
                    webhookUrl: this.getEnv('SLACK_WEBHOOK_URL', ''),
                    enabled: !!this.getEnv('SLACK_WEBHOOK_URL', ''),
                },
                webhook: {
                    secretKey: this.getEnv('WEBHOOK_SECRET_KEY', 'your-secret-key'),
                },
            },

            // ========== TRADING ==========
            trading: {
                enabled: this.getBoolean('TRADING_ENABLED', false),
                autoTradingEnabled: this.getBoolean('AUTO_TRADING_ENABLED', false),
                maxPositionSize: parseFloat(this.getEnv('MAX_POSITION_SIZE', '1000')),
                riskPerTrade: parseFloat(this.getEnv('RISK_PER_TRADE', '2')),
            },

            // ========== EXCHANGES ==========
            exchanges: {
                binance: {
                    apiKey: this.getEnv('BINANCE_API_KEY', ''),
                    secret: this.getEnv('BINANCE_SECRET', ''),
                    enabled: !!this.getEnv('BINANCE_API_KEY', ''),
                },
                dexscreener: {
                    apiKey: this.getEnv('DEXSCREENER_API_KEY', ''),
                    enabled: !!this.getEnv('DEXSCREENER_API_KEY', ''),
                },
            },

            // ========== SECURITY ==========
            security: {
                jwtSecret: this.getEnv('JWT_SECRET', 'your-super-secret-jwt-key-change-this'),
                jwtExpiry: this.getEnv('JWT_EXPIRY', '24h'),
                encryptionKey: this.getEnv('ENCRYPTION_KEY', 'your-encryption-key-32-chars-long'),
            },

            // ========== LOGGING ==========
            logging: {
                level: this.getEnv('LOG_LEVEL', 'info'),
                file: this.getEnv('LOG_FILE', 'logs/app.log'),
            },

            // ========== FEATURES ==========
            features: {
                enablePumpX: this.getBoolean('ENABLE_PUMPX', true),
                enableAlphaSignals: this.getBoolean('ENABLE_ALPHA_SIGNALS', true),
                enableAutoTrading: this.getBoolean('ENABLE_AUTO_TRADING', false),
                debugMode: this.getBoolean('DEBUG_MODE', false),
            },

            // ========== SYSTEM ==========
            system: {
                name: this.getEnv('SYSTEM_NAME', 'CryptoTrader V2'),
                version: this.getEnv('VERSION', '2.0.0'),
            },

            // ========== PLATFORM ==========
            platform: {
                isWindows: this.isWindows,
                isLinux: this.isLinux,
                isDevelopment: this.isDevelopment,
            },
        };
    }

    /**
     * Get environment variable with fallback
     */
    getEnv(key, defaultValue = null) {
        const value = process.env[key];
        return value !== undefined ? value : defaultValue;
    }

    /**
     * Get boolean environment variable
     */
    getBoolean(key, defaultValue = false) {
        const value = this.getEnv(key, String(defaultValue));
        return value === 'true' || value === '1' || value === true;
    }

    /**
     * Validate required configuration
     */
    validateRequired() {
        const required = [
            'database.connectionString',
        ];

        required.forEach(key => {
            if (!this.getConfigValue(key)) {
                this.errors.push(`Missing required config: ${key}`);
            }
        });

        if (this.errors.length > 0) {
            console.warn('[CONFIG] Warnings detected:');
            this.errors.forEach(err => console.warn(`  ⚠️  ${err}`));
            console.warn('[CONFIG] Set via Admin Portal > Settings > Database\n');
        }
    }

    /**
     * Get nested config value using dot notation
     */
    getConfigValue(path) {
        return path.split('.').reduce((obj, key) => obj?.[key], this.config);
    }

    /**
     * Get full configuration object
     */
    getConfig() {
        return this.config;
    }

    /**
     * Get database connection string or build from parts
     */
    getDatabaseConnectionString() {
        const { connectionString, user, password, host, port, database } = this.config.database;
        
        if (connectionString) {
            return connectionString;
        }
        
        return `postgresql://${user}:${password}@${host}:${port}/${database}`;
    }

    /**
     * Get database config object for pg library
     */
    getDatabaseConfig() {
        return {
            host: this.config.database.host,
            port: this.config.database.port,
            user: this.config.database.user,
            password: this.config.database.password,
            database: this.config.database.database,
        };
    }

    /**
     * Print configuration (excluding secrets)
     */
    printConfig() {
        const safe = JSON.parse(JSON.stringify(this.config));
        
        // Mask sensitive values
        if (safe.database.password) safe.database.password = '***';
        if (safe.security.jwtSecret) safe.security.jwtSecret = '***';
        if (safe.security.encryptionKey) safe.security.encryptionKey = '***';
        if (safe.notifications.telegram.botToken) safe.notifications.telegram.botToken = '***';
        if (safe.exchanges.binance.apiKey) safe.exchanges.binance.apiKey = '***';
        if (safe.exchanges.binance.secret) safe.exchanges.binance.secret = '***';
        
        console.log('[CONFIG] Loaded configuration:');
        console.log(JSON.stringify(safe, null, 2));
    }

    /**
     * Export for use in other files
     */
    static getInstance() {
        if (!ConfigLoader.instance) {
            ConfigLoader.instance = new ConfigLoader();
        }
        return ConfigLoader.instance;
    }
}

// Create singleton instance
const config = new ConfigLoader();

module.exports = config;
