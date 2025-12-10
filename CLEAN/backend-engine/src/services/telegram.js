import fetch from "node-fetch";
import dotenv from "dotenv";
dotenv.config();

export async function sendTelegramMessage(text) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;

  if (!token || !chatId) {
    console.warn("[TELEGRAM] Missing token or chat ID, skipping send.");
    return;
  }

  const url = `https://api.telegram.org/bot${token}/sendMessage`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text })
    });
    if (!res.ok) {
      const txt = await res.text();
      console.warn("[TELEGRAM] sendMessage failed:", res.status, txt);
    }
  } catch (err) {
    console.warn("[TELEGRAM] Error sending:", err.message);
  }
}
