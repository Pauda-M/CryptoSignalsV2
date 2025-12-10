/**
 * DatabaseConfig.js - Portable PostgreSQL configuration
 * Manages database initialization and connection setup
 * Works on Linux and Windows
 */

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const config = require('./ConfigLoader');

class DatabaseConfig {
    constructor() {
        this.pool = null;
        this.isInitialized = false;
    }

    /**
     * Initialize database connection pool
     */
    async initialize() {
        try {
            const dbConfig = config.getDatabaseConfig();
            
            this.pool = new Pool({
                ...dbConfig,
                max: 20,
                idleTimeoutMillis: 30000,
                connectionTimeoutMillis: 2000,
            });

            // Test connection
            const client = await this.pool.connect();
            await client.query('SELECT NOW()');
            client.release();
            
            this.isInitialized = true;
            console.log('[DB] ✅ Database connection established');
            
            return true;
        } catch (error) {
            console.error('[DB] ❌ Failed to connect to database:', error.message);
            throw error;
        }
    }

    /**
     * Get database pool
     */
    getPool() {
        if (!this.pool) {
            throw new Error('Database not initialized. Call initialize() first.');
        }
        return this.pool;
    }

    /**
     * Execute query
     */
    async query(sql, params = []) {
        if (!this.pool) {
            throw new Error('Database not initialized');
        }
        return this.pool.query(sql, params);
    }

    /**
     * Get single row
     */
    async getOne(sql, params = []) {
        const result = await this.query(sql, params);
        return result.rows[0] || null;
    }

    /**
     * Get all rows
     */
    async getAll(sql, params = []) {
        const result = await this.query(sql, params);
        return result.rows;
    }

    /**
     * Run schema migration (from file or string)
     */
    async runMigration(migrationPath) {
        try {
            let sql;
            
            if (fs.existsSync(migrationPath)) {
                sql = fs.readFileSync(migrationPath, 'utf8');
            } else {
                sql = migrationPath; // Assume it's SQL string
            }

            await this.pool.query(sql);
            console.log('[DB] ✅ Migration completed');
            return true;
        } catch (error) {
            console.error('[DB] ❌ Migration failed:', error.message);
            throw error;
        }
    }

    /**
     * Close connection pool
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
            console.log('[DB] Connection pool closed');
        }
    }

    /**
     * Get connection string from environment
     */
    static getConnectionString() {
        return config.getDatabaseConnectionString();
    }

    /**
     * Singleton instance
     */
    static getInstance() {
        if (!DatabaseConfig.instance) {
            DatabaseConfig.instance = new DatabaseConfig();
        }
        return DatabaseConfig.instance;
    }
}

module.exports = DatabaseConfig;
