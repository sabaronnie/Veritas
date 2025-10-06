const $ = (s) => document.querySelector(s);
const statusEl = $("#status");
const claimsEl = $("#claims");
const verdictEl = $("#verdict");

function badge(label) {
  const map = { "Core":"core", "Partial":"partial", "Disputed":"disputed", "Unknown":"unknown" };
  return `<span class="badge ${map[label] || "unknown"}">${label}</span>`;
}

async function getPagePayload() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, { type: "VERITAS_GET_PAGE" }, (resp) => {
        resolve(resp?.payload);
      });
    });
  });
}

async function analyze() {
  claimsEl.innerHTML = "";
  verdictEl.textContent = "";
  statusEl.textContent = "Extracting page…";
  const payload = await getPagePayload();
  if (!payload?.text || payload.text.length < 120) {
    statusEl.textContent = "Couldn't extract enough text on this page.";
    return;
  }
  statusEl.textContent = "Contacting Veritas…";
  chrome.runtime.sendMessage({ type: "VERITAS_ANALYZE_PAGE", payload }, (resp) => {
    if (!resp?.ok) {
      statusEl.textContent = `Error: ${resp?.error || "unknown"}`;
      return;
    }
    const data = resp.data;
    statusEl.textContent = "";
    verdictEl.textContent = `Overall: ${data.verdict.label} (score ${Math.round(data.verdict.score*100)/100})`;

    for (const c of data.claims) {
      const ev = (c.evidence || []).slice(0, 4).map(e =>
        `<a href="${e.url}" target="_blank">${e.source || new URL(e.url).hostname}</a> (${e.stance})`
      ).join(" • ");
      claimsEl.insertAdjacentHTML("beforeend",
        `<li class="claim">
           ${badge(c.label)} ${c.text}
           <div class="evidence">${ev}</div>
         </li>`);
    }
  });
}

$("#analyze").addEventListener("click", analyze);
