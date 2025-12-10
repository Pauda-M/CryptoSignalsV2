const API_BASE = "/api/pumpx";

/* ---------------------- Helpers ---------------------- */

async function safeGet(url) {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const text = await res.text();
        if (!text) return null;

        try {
            return JSON.parse(text);
        } catch (err) {
            console.error("JSON parse error for:", url, err, "body:", text);
            return null;
        }
    } catch (err) {
        console.error("Fetch error:", url, err);
        return null;
    }
}

/* ---------------------- API Calls ---------------------- */

export async function getRadar(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await safeGet(`${API_BASE}/radar?${query}`);
}

export async function getAlerts() {
    return await safeGet(`${API_BASE}/alerts`);
}

export async function getLive() {
    return await safeGet(`${API_BASE}/live`);
}

export async function searchToken(q) {
    return await safeGet(`${API_BASE}/search?q=${encodeURIComponent(q)}`);
}

export async function getHourlyHistory(mint) {
    return await safeGet(`${API_BASE}/history/${mint}`);
}

/* ---------------------- Default Export ---------------------- */

export default {
    getRadar,
    getAlerts,
    getLive,
    searchToken,
    getHourlyHistory,
};
