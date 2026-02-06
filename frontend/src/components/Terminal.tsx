import "@xterm/xterm/css/xterm.css";

import { FitAddon } from "@xterm/addon-fit";
import { Terminal as XTerm } from "@xterm/xterm";
import { useEffect, useRef } from "react";

import { config } from "../config";

interface TerminalProps {
  sessionId: string;
  wsToken: string;
  onReady?: () => void;
  onLevelComplete?: () => void;
}

export function Terminal({
  sessionId,
  wsToken,
  onReady,
  onLevelComplete,
}: TerminalProps) {
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

      // Plain WebSocket to local Express server — no subprotocol, no ttyd
      const wsUrl = `${config.apiUrl.replace("http", "ws")}/ws/terminal/${sessionId}?token=${wsToken}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isActive) return;
        reconnectAttemptRef.current = 0;
        onReadyRef.current?.();
      };

      ws.onmessage = (event) => {
        if (!isActive) return;
        const data = event.data;

        if (typeof data === "string") {
          if (data.includes("__LEVEL_COMPLETE__")) {
            term.write(data.replace("__LEVEL_COMPLETE__", ""));
            onLevelCompleteRef.current?.();
            return;
          }
          term.write(data);
        }
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

      // Input — plain text, no type prefix
      term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(data);
        }
      });
    };

    // Initial connection with small delay
    const connectTimeout = setTimeout(connect, 100);

    // Handle resize — send as JSON
    const handleResize = () => {
      fitAddon.fit();
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        const dims = fitAddon.proposeDimensions();
        if (dims) {
          ws.send(JSON.stringify({ cols: dims.cols, rows: dims.rows }));
        }
      }
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
  }, [sessionId, wsToken]);

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
