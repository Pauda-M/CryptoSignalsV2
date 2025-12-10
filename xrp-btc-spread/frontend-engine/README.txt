Dashboard Full Extension

This package contains a full replacement dashboard with:
- Extended Futures tab (raw + spread futures signals)
- New Copy Trading tab (settings + signals + 'Set position' button)
- Settings card with localStorage persistence
- All basic tabs (Predictions, Futures, Wallets, Summary, Logs, Copy Trading)

Install:
1. In your project, replace frontend-engine/services/dashboard-app/public/index.html
   with the index.html from this zip.
2. Replace or add frontend-engine/services/dashboard-app/server.js and package.json
   if needed.
3. Restart your frontend: run_frontend.bat or launcher.bat and open http://localhost:8080
4. Make sure backend endpoints exist:
   - /api/predictions
   - /api/futures (returns { raw: [...], spread_signals: [...] })
   - /api/wallets
   - /api/summary
   - /api/copy/settings
   - /api/copy/signals
   - /api/copy/signals/{id}/set_position
