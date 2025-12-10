/**
 * Database Initialization Script
 * Creates schema and tables for CryptoTrader V2
 * Compatible with Linux and Windows
 */

require('dotenv').config({ path: '../../.env' });
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

const config = require('../../config/ConfigLoader');

async function initDatabase() {
    const pool = new Pool(config.getDatabaseConfig());

    try {
        console.log('[DB] Starting database initialization...');
        
        // Read schema file
        const schemaPath = path.join(__dirname, 'schema.sql');
        if (!fs.existsSync(schemaPath)) {
            throw new Error(`Schema file not found: ${schemaPath}`);
        }
        
        const schema = fs.readFileSync(schemaPath, 'utf8');
        
        // Execute schema
        await pool.query(schema);
        console.log('[DB] ✅ Database schema created successfully');
        
        // Seed initial data if seed file exists
        const seedPath = path.join(__dirname, '../seeds/init-seed.sql');
        if (fs.existsSync(seedPath)) {
            const seedData = fs.readFileSync(seedPath, 'utf8');
            await pool.query(seedData);
            console.log('[DB] ✅ Initial data seeded successfully');
        }
        
    } catch (error) {
        console.error('[DB] ❌ Initialization failed:', error.message);
        process.exit(1);
    } finally {
        await pool.end();
    }
}

initDatabase();
