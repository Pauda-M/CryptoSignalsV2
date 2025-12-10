export async function getRadar() {
    return fetch("/api/pumpx/radar").then(r => r.json());
}

export async function getTrends() {
    return fetch("/api/pumpx/trends").then(r => r.json());
}

export async function getAlphaSignals() {
    return fetch("/api/signals").then(r => r.json());
}

export async function getAssets() {
    return fetch("/api/assets").then(r => r.json());
}
