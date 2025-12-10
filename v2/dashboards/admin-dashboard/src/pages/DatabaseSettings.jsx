/**
 * DatabaseSettings.jsx - Admin Portal Database Configuration
 * Allows setting PostgreSQL connection string via UI
 * Stores in system_config table
 */

import React, { useState, useEffect } from 'react';

export default function DatabaseSettings() {
    const [connectionString, setConnectionString] = useState('');
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');
    const [statusType, setStatusType] = useState('info');

    useEffect(() => {
        fetchCurrentConnection();
    }, []);

    const fetchCurrentConnection = async () => {
        try {
            const response = await fetch('/api/admin/config/database');
            const data = await response.json();
            if (data.connectionString) {
                // Mask password for display
                const masked = data.connectionString.replace(/(:)([^:@]*)(@)/g, '$1***$3');
                setConnectionString(masked);
            }
        } catch (error) {
            console.error('Failed to fetch connection string:', error);
        }
    };

    const testConnection = async (connStr) => {
        try {
            const response = await fetch('/api/admin/db/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ connectionString: connStr })
            });
            
            const data = await response.json();
            if (response.ok) {
                setStatus('✅ Database connection successful!');
                setStatusType('success');
                return true;
            } else {
                setStatus(`❌ Connection failed: ${data.error}`);
                setStatusType('error');
                return false;
            }
        } catch (error) {
            setStatus(`❌ Error: ${error.message}`);
            setStatusType('error');
            return false;
        }
    };

    const handleSave = async () => {
        if (!connectionString.trim()) {
            setStatus('⚠️ Connection string cannot be empty');
            setStatusType('warning');
            return;
        }

        setLoading(true);
        
        try {
            // Test connection first
            const testSuccess = await testConnection(connectionString);
            if (!testSuccess) {
                setLoading(false);
                return;
            }

            // Save to database
            const response = await fetch('/api/admin/config/database', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ connectionString })
            });

            if (response.ok) {
                setStatus('✅ Database configuration saved successfully!');
                setStatusType('success');
                
                // Reload environment
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                const data = await response.json();
                setStatus(`❌ Failed to save: ${data.error}`);
                setStatusType('error');
            }
        } catch (error) {
            setStatus(`❌ Error: ${error.message}`);
            setStatusType('error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 bg-white rounded-lg shadow">
            <h2 className="text-2xl font-bold mb-6">Database Configuration</h2>
            
            <div className="mb-6 p-4 bg-blue-50 border-l-4 border-blue-500 rounded">
                <p className="text-sm text-gray-700">
                    <strong>PostgreSQL Connection String Format:</strong><br/>
                    postgresql://username:password@host:port/database<br/>
                    Example: postgresql://postgres:password123@localhost:5432/crypto_signals_v2
                </p>
            </div>

            <div className="mb-4">
                <label className="block text-gray-700 font-semibold mb-2">
                    Connection String
                </label>
                <input
                    type="password"
                    value={connectionString}
                    onChange={(e) => setConnectionString(e.target.value)}
                    placeholder="postgresql://user:password@localhost:5432/crypto_signals_v2"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
            </div>

            {status && (
                <div className={`mb-4 p-3 rounded ${
                    statusType === 'success' ? 'bg-green-100 text-green-700' :
                    statusType === 'error' ? 'bg-red-100 text-red-700' :
                    statusType === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-blue-100 text-blue-700'
                }`}>
                    {status}
                </div>
            )}

            <div className="flex gap-2">
                <button
                    onClick={() => testConnection(connectionString)}
                    disabled={loading}
                    className="px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50"
                >
                    Test Connection
                </button>
                <button
                    onClick={handleSave}
                    disabled={loading}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                    {loading ? 'Saving...' : 'Save Configuration'}
                </button>
            </div>

            <div className="mt-8 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold mb-2">Environment Variable (.env)</h3>
                <p className="text-sm text-gray-600 font-mono">
                    DB_CONNECTION_STRING=postgresql://user:password@localhost:5432/crypto_signals_v2
                </p>
            </div>
        </div>
    );
}
