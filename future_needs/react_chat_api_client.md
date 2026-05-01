// src/api/dealerAi.js

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function startDealerChat() {
  const res = await fetch(`${API_BASE}/api/dealer-ai/chat/start/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) throw new Error("Failed to start chat");
  return res.json();
}

export async function sendDealerMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/api/dealer-ai/chat/message/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
    }),
  });

  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function createDealerLead(payload) {
  const res = await fetch(`${API_BASE}/api/dealer-ai/leads/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) throw new Error("Failed to create lead");
  return res.json();
}