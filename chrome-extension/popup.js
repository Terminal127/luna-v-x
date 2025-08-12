// popup.js - sends messages to the background service worker which forwards them to the MCP server
function log(msg) {
  const out = document.getElementById("out");
  out.textContent = (out.textContent ? out.textContent + "\n" : "") + msg;
}

function sendToBackground(msg, cb) {
  chrome.runtime.sendMessage(msg, (resp) => {
    cb && cb(resp);
  });
}

// List tabs
document.getElementById("btnList").addEventListener("click", () => {
  sendToBackground({ type: "command", command: "list_tabs" }, () => {
    log("List request sent.");
  });
});

// Open tab (background by default)
document.getElementById("btnOpen").addEventListener("click", () => {
  const url = document.getElementById("openUrl").value.trim();
  if (!url) return log("Provide a URL to open.");
  sendToBackground(
    { type: "command", command: "open_tab", payload: { url, active: false } }, // active: false keeps it in background
    () => {
      log("Open request sent: " + url);
    },
  );
});

// Do action on a tab
document.getElementById("btnDo").addEventListener("click", () => {
  const cmd = document.getElementById("cmdSelect").value; // "close", "switch", "reload", "navigate"
  const tabIdRaw = document.getElementById("tabId").value.trim();
  const tabId = tabIdRaw ? parseInt(tabIdRaw, 10) : null;
  const navUrl = document.getElementById("navUrl").value.trim();

  const payload = {};
  if (tabId !== null && !Number.isNaN(tabId)) payload.tabId = tabId;

  if (cmd === "navigate") {
    if (!navUrl) return log("Provide URL for navigation.");
    payload.url = navUrl;
    sendToBackground(
      { type: "command", command: "navigate_tab", payload },
      () => log(`Navigate request sent to tab ${tabId} → ${navUrl}`),
    );
  } else if (cmd === "close") {
    sendToBackground({ type: "command", command: "close_tab", payload }, () =>
      log(`Close request sent for tab ${tabId}`),
    );
  } else if (cmd === "switch") {
    sendToBackground({ type: "command", command: "switch_tab", payload }, () =>
      log(`Switch request sent for tab ${tabId}`),
    );
  } else if (cmd === "reload") {
    sendToBackground({ type: "command", command: "reload_tab", payload }, () =>
      log(`Reload request sent for tab ${tabId}`),
    );
  } else {
    log("Unknown command.");
  }
});
