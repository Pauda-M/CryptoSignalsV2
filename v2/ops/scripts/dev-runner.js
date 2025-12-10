/*
 * dev-runner.js
 * Start multiple services in development mode concurrently.
 * Cross-platform: uses shell spawns so works on Windows PowerShell and Unix shells.
 * Location: v2/ops/scripts/dev-runner.js
 *
 * Usage: node ops/scripts/dev-runner.js
 */

const { spawn } = require('child_process');
const path = require('path');

const services = [
  'services/api-gateway',
  'services/trading-engine',
  'services/notification-service',
  'services/websocket-streamer',
  'services/data-aggregator',
  // Add others as needed
];

const children = [];

function startService(servicePath) {
  const abs = path.join(process.cwd(), servicePath);
  // Use npm run dev, fall back to npm start if dev unavailable
  const cmd = `npm run dev --prefix "${abs}" || npm start --prefix "${abs}"`;
  console.log(`\n[dev-runner] Starting: ${servicePath}`);

  const child = spawn(cmd, { shell: true, stdio: 'inherit' });
  children.push(child);

  child.on('exit', (code, signal) => {
    console.log(`[dev-runner] Process ${servicePath} exited with code=${code}, signal=${signal}`);
  });
  child.on('error', (err) => {
    console.error(`[dev-runner] Failed to start ${servicePath}:`, err.message);
  });
}

function shutdown() {
  console.log('\n[dev-runner] Shutting down child processes...');
  children.forEach((c) => {
    try {
      if (c && !c.killed) {
        // Attempt graceful termination
        c.kill('SIGINT');
      }
    } catch (e) {
      // ignore
    }
  });
  setTimeout(() => process.exit(0), 1000);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

(async () => {
  console.log('[dev-runner] Starting development services...');

  for (const s of services) {
    startService(s);
    // small delay to stagger starts
    await new Promise((r) => setTimeout(r, 300));
  }

  console.log('[dev-runner] All start commands issued. Press Ctrl+C to stop.');
})();
