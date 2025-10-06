// Lightweight text extractor (works for most news sites)
function visible(el) {
  const style = window.getComputedStyle(el);
  return style && style.display !== "none" && style.visibility !== "hidden";
}
function getMainText() {
  let txt = "";
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
  let node;
  while ((node = walker.nextNode())) {
    const parent = node.parentElement;
    if (!parent) continue;
    const tag = parent.tagName.toLowerCase();
    if (["script","style","noscript","svg","path","iframe","nav","footer","header"].includes(tag)) continue;
    if (visible(parent)) {
      const t = node.nodeValue.replace(/\s+/g, " ").trim();
      if (t.length > 0) txt += t + " ";
    }
  }
  return txt.trim();
}

// Cache latest extraction for popup to request
let latestPayload = null;
function refreshPayload() {
  latestPayload = {
    url: location.href,
    title: document.title,
    text: getMainText().slice(0, 150000) // guard size
  };
}
refreshPayload();

// Listen for popup requests
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "VERITAS_GET_PAGE") {
    refreshPayload();
    sendResponse({ ok: true, payload: latestPayload });
  }
  return true;
});
