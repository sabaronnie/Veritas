const DEFAULT_API_BASE = "http://localhost:8000"; // change after deploy

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ apiBase: DEFAULT_API_BASE });
});

async function analyzeText(payload) {
  const { apiBase } = await chrome.storage.sync.get("apiBase");
  const endpoint = `${apiBase || DEFAULT_API_BASE}/analyze_text`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

// Handle popup analysis requests
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (msg?.type === "VERITAS_ANALYZE_PAGE") {
      try {
        const data = await analyzeText(msg.payload);
        sendResponse({ ok: true, data });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
    }
  })();
  return true;
});
