import "@xterm/xterm/css/xterm.css";

import { FitAddon } from "@xterm/addon-fit";
import { Terminal as XTerm } from "@xterm/xterm";
import { useEffect, useRef } from "react";

import { config } from "../config";

interface TerminalProps {
  sessionId: string;
  ttydUrl?: string; // If provided, use iframe mode (Fly.io/Docker)
  ttydPort?: number; // For Docker mode: port where ttyd is running
  ttydToken?: string; // For Docker mode: authentication token
  onReady?: () => void;
  onLevelComplete?: () => void;
}

// Iframe-based terminal for Fly.io/Docker ttyd
function IframeTerminal({
  ttydUrl,
  ttydPort,
  ttydToken,
  onReady,
}: {
  ttydUrl?: string;
  ttydPort?: number;
  ttydToken?: string;
  onReady?: () => void;
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Determine the URL to use
  // For Docker mode: construct URL with basic auth
  // For Fly.io mode: use the provided ttydUrl directly
  //
  // SECURITY NOTE: Credentials in URL is acceptable for LOCAL DEVELOPMENT ONLY.
  // The ttyd token is ephemeral (per-session) and the URL is localhost.
  // For production deployment, use a backend proxy or cookie-based auth.
  const terminalUrl = ttydUrl
    ? ttydUrl
    : ttydPort && ttydToken
      ? `http://user:${ttydToken}@localhost:${ttydPort}/`
      : null;

  useEffect(() => {
    // Notify ready when iframe loads
    const iframe = iframeRef.current;
    if (iframe) {
      iframe.onload = () => {
        onReady?.();
      };
    }
  }, [onReady]);

  if (!terminalUrl) {
    return (
      <div style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#1a1a2e",
        color: "#eee",
      }}>
        <p>Terminal configuration missing</p>
      </div>
    );
  }

  return (
    <iframe
      ref={iframeRef}
      src={terminalUrl}
      title="Terminal"
      style={{
        width: "100%",
        height: "100%",
        border: "none",
        backgroundColor: "#1a1a2e",
      }}
      allow="clipboard-read; clipboard-write"
    />
  );
}

// WebSocket-based terminal for local/Modal/Fly mode
function WebSocketTerminal({
  sessionId,
  onReady,
  onLevelComplete,
}: {
  sessionId: string;
  onReady?: () => void;
  onLevelComplete?: () => void;
}) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptRef = useRef(0);

  const onReadyRef = useRef(onReady);
  const onLevelCompleteRef = useRef(onLevelComplete);
  onReadyRef.current = onReady;
  onLevelCompleteRef.current = onLevelComplete;

  useEffect(() => {
    if (!terminalRef.current) return;

    let isActive = true;
    const MAX_RECONNECT_ATTEMPTS = 5;
    const RECONNECT_DELAY_MS = 2000;

    // Create terminal
    const term = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: "#1a1a2e",
        foreground: "#eee",
        cursor: "#f0f0f0",
        cursorAccent: "#1a1a2e",
        selectionBackground: "#6366f1",
      },
    });

    const fitAddon = new FitAddon();
    fitAddonRef.current = fitAddon;
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();
    term.focus();

    xtermRef.current = term;

    const connect = () => {
      if (!isActive) return;

      // Connect to backend WebSocket proxy
      const wsUrl = `${config.apiUrl.replace("http", "ws")}/ws/terminal/${sessionId}`;
      // ttyd requires the 'tty' subprotocol
      const ws = new WebSocket(wsUrl, ["tty"]);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isActive) return;
        reconnectAttemptRef.current = 0; // Reset on successful connection
        onReadyRef.current?.();
      };

      ws.onmessage = (event) => {
        if (!isActive) return;
        const data = event.data;

        // Ignore empty keepalive pings
        if (data === "" || (data instanceof Blob && data.size === 0)) {
          return;
        }

        // Check for level complete marker
        if (typeof data === "string" && data.includes("__LEVEL_COMPLETE__")) {
          const cleanData = data.replace("__LEVEL_COMPLETE__", "");
          if (cleanData.trim()) {
            term.write(cleanData);
          }
          onLevelCompleteRef.current?.();
          return;
        }

        term.write(data);
      };

      ws.onerror = () => {
        if (!isActive) return;
        // Error will be followed by close, handle reconnection there
      };

      ws.onclose = (event) => {
        if (!isActive) return;

        // Don't reconnect if closed cleanly (code 1000) or session not found (1008)
        if (event.code === 1000 || event.code === 1008) {
          term.writeln("\r\n\x1b[33mDisconnected\x1b[0m");
          return;
        }

        // Attempt reconnection
        if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptRef.current++;
          term.writeln(
            `\r\n\x1b[33mConnection lost. Reconnecting (${reconnectAttemptRef.current}/${MAX_RECONNECT_ATTEMPTS})...\x1b[0m`
          );
          reconnectTimeoutRef.current = window.setTimeout(
            connect,
            RECONNECT_DELAY_MS
          );
        } else {
          term.writeln(
            "\r\n\x1b[31mConnection lost. Please refresh the page.\x1b[0m"
          );
        }
      };

      // Send input to backend
      term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(data);
        }
      });
    };

    // Initial connection with small delay
    const connectTimeout = setTimeout(connect, 100);

    // Handle resize
    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      isActive = false;
      clearTimeout(connectTimeout);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      window.removeEventListener("resize", handleResize);
      if (wsRef.current) {
        wsRef.current.close(1000); // Clean close
      }
      term.dispose();
    };
  }, [sessionId]);

  return (
    <div
      ref={terminalRef}
      style={{
        width: "100%",
        height: "100%",
        padding: "10px",
        backgroundColor: "#1a1a2e",
      }}
    />
  );
}

export function Terminal({
  sessionId,
  ttydUrl,
  ttydPort,
  ttydToken,
  onReady,
  onLevelComplete,
}: TerminalProps) {
  // Use iframe for Fly.io (ttydUrl provided) or Docker mode (ttydPort + ttydToken)
  if (ttydUrl || (ttydPort && ttydToken)) {
    return (
      <IframeTerminal
        ttydUrl={ttydUrl}
        ttydPort={ttydPort}
        ttydToken={ttydToken}
        onReady={onReady}
      />
    );
  }

  // WebSocket mode for local/Modal
  return (
    <WebSocketTerminal
      sessionId={sessionId}
      onReady={onReady}
      onLevelComplete={onLevelComplete}
    />
  );
}
