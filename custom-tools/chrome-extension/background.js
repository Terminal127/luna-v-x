// background.js - Persistent-ish WebSocket connection for MV3
const MCP_WS = "ws://127.0.0.1:8765/ws"; // Use 127.0.0.1 instead of localhost for reliability
let socket = null;
let reconnectTimer = null;
let pingTimer = null;
const RECONNECT_DELAY = 3000; // 3 seconds
const PING_INTERVAL = 20000; // 20 seconds

function connect() {
  if (socket && socket.readyState === WebSocket.OPEN) {
    console.log("[MCP EXT] Already connected.");
    return;
  }

  try {
    socket = new WebSocket(MCP_WS);

    socket.addEventListener("open", () => {
      console.log("[MCP EXT] Connected to MCP server.");
      socket.send(JSON.stringify({ type: "role", role: "extension" }));

      // Start ping interval
      if (pingTimer) clearInterval(pingTimer);
      pingTimer = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "ping", ts: Date.now() }));
        }
      }, PING_INTERVAL);
    });

    socket.addEventListener("message", async (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "command") {
          const id = msg.id || null;
          const cmd = msg.command;
          const payload = msg.payload || {};

          const respond = (result, error = null) => {
            socket.send(
              JSON.stringify({
                type: "response",
                id,
                result: error ? undefined : result,
                error: error || undefined,
              }),
            );
          };

          if (cmd === "list_tabs") {
            const tabs = await chrome.tabs.query({});
            respond(tabs);
          } else if (cmd === "open_tab") {
            const t = await chrome.tabs.create({
              url: payload.url || "about:blank",
              active: false,
            });
            respond(t);
          } else if (cmd === "close_tab") {
            if (payload.tabId != null) {
              await chrome.tabs.remove(payload.tabId);
              respond({ closed: payload.tabId });
            } else respond(null, "missing_tabId");
          } else if (cmd === "switch_tab") {
            if (payload.tabId != null) {
              await chrome.tabs.update(payload.tabId, { active: true });
              if (payload.windowId)
                await chrome.windows.update(payload.windowId, {
                  focused: true,
                });
              respond({ switched: payload.tabId });
            } else respond(null, "missing_tabId");
          } else if (cmd === "reload_tab") {
            if (payload.tabId != null) {
              await chrome.tabs.reload(payload.tabId);
              respond({ reloaded: payload.tabId });
            } else respond(null, "missing_tabId");
          } else if (cmd === "navigate_tab") {
            if (payload.tabId != null && payload.url) {
              await chrome.tabs.update(payload.tabId, { url: payload.url });
              respond({ navigated: payload.tabId });
            } else respond(null, "missing_tabId_or_url");
          } else {
            respond(null, "unknown_command");
          }
        }
      } catch (err) {
        console.error("[MCP EXT] message handling error:", err);
      }
    });

    socket.addEventListener("close", () => {
      console.warn("[MCP EXT] Connection closed. Reconnecting...");
      cleanupSocket();
      scheduleReconnect();
    });

    socket.addEventListener("error", (e) => {
      console.error("[MCP EXT] Socket error:", e);
      cleanupSocket();
      scheduleReconnect();
    });
  } catch (err) {
    console.error("[MCP EXT] connect() error:", err);
    scheduleReconnect();
  }
}

function cleanupSocket() {
  if (pingTimer) clearInterval(pingTimer);
  pingTimer = null;
  socket = null;
}

function scheduleReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connect, RECONNECT_DELAY);
}

// Alarm to keep service worker alive & reconnect if unloaded
chrome.alarms.create("mcp_keepalive", { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "mcp_keepalive") {
    console.log("[MCP EXT] Keepalive alarm triggered.");
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      connect();
    }
  }
});

// Reconnect on extension start
connect();

// Optional: popup or other extension pages can send messages
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(msg));
    sendResponse({ sent: true });
  } else {
    sendResponse({ sent: false, reason: "socket_not_open" });
  }
  return true;
});
