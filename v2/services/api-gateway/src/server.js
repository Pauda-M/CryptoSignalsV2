/**
 * API Gateway Server - CryptoTrader V2
 * Main REST API entry point
 * Runs on configurable port (default: 3000)
 */

require('dotenv').config({ path: '../../.env' });
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const { Pool } = require('pg');
const config = require('../../config/ConfigLoader');

const app = express();

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Database Pool
const pool = new Pool(config.getDatabaseConfig());

// Health Check
app.get('/api/health', async (req, res) => {
    try {
        const result = await pool.query('SELECT NOW()');
        res.json({ 
            status: 'ok', 
            timestamp: result.rows[0].now,
            database: 'connected'
        });
    } catch (error) {
        res.status(500).json({ 
            status: 'error', 
            message: error.message,
            database: 'disconnected'
        });
    }
});

// Database Status
app.get('/api/status/db', async (req, res) => {
    try {
        const result = await pool.query('SELECT version()');
        res.json({ 
            status: 'connected',
            database: result.rows[0].version
        });
    } catch (error) {
        res.status(500).json({ 
            status: 'error', 
            message: error.message
        });
    }
});

// Config Status (non-sensitive)
app.get('/api/status/config', (req, res) => {
    res.json({
        system: 'CryptoTrader V2',
        api: {
            port: config.config.api.port,
            host: config.config.api.host,
        },
        database: {
            host: config.config.database.host,
            port: config.config.database.port,
            database: config.config.database.database,
        },
        platform: config.config.platform,
    });
});

// Error handler
app.use((err, req, res, next) => {
    console.error(err);
    res.status(500).json({ error: err.message });
});

// Start server
const PORT = config.config.api.port;
const HOST = config.config.api.host;

app.listen(PORT, HOST, () => {
    console.log(`[API Gateway] Server running on ${HOST}:${PORT}`);
    console.log(`[API Gateway] Health check: http://localhost:${PORT}/api/health`);
});
