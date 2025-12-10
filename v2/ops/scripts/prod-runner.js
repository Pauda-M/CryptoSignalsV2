/*
 * prod-runner.js
 * Start production services (uses `npm start` for each service path)
 * Location: v2/ops/scripts/prod-runner.js
 *
 * Usage: node ops/scripts/prod-runner.js
 */

const { spawn } = require('child_process');
const path = require('path');

const services = [
  'services/api-gateway',
  'services/trading-engine',
  'services/notification-service',
  'services/websocket-streamer',
  'services/data-aggregator'
];

const children = [];

function startService(servicePath) {
  const abs = path.join(process.cwd(), servicePath);
  const cmd = `npm start --prefix "${abs}"`;
  console.log(`\n[prod-runner] Starting: ${servicePath}`);

  const child = spawn(cmd, { shell: true, stdio: 'inherit' });
  children.push(child);

  child.on('exit', (code, signal) => {
    console.log(`[prod-runner] Process ${servicePath} exited with code=${code}, signal=${signal}`);
  });
  child.on('error', (err) => {
    console.error(`[prod-runner] Failed to start ${servicePath}:`, err.message);
  });
}

function shutdown() {
  console.log('\n[prod-runner] Shutting down child processes...');
  children.forEach((c) => {
    try {
      if (c && !c.killed) {
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
  console.log('[prod-runner] Starting production services...');

  for (const s of services) {
    startService(s);
    await new Promise((r) => setTimeout(r, 300));
  }

  console.log('[prod-runner] All start commands issued.');
})();
