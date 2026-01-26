import "@xterm/xterm/css/xterm.css";

import { FitAddon } from "@xterm/addon-fit";
import { Terminal as XTerm } from "@xterm/xterm";
import { useEffect, useRef } from "react";

interface TerminalProps {
  sessionId: string;
  onReady?: () => void;
  onLevelComplete?: () => void;
}

export function Terminal({
  sessionId,
  onReady,
  onLevelComplete,
}: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Store callbacks in refs to avoid effect re-runs
  const onReadyRef = useRef(onReady);
  const onLevelCompleteRef = useRef(onLevelComplete);
  onReadyRef.current = onReady;
  onLevelCompleteRef.current = onLevelComplete;

  useEffect(() => {
    if (!terminalRef.current) return;

    // Track if effect is still active (for strict mode cleanup)
    let isActive = true;

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
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;

    // Connect WebSocket with small delay to avoid strict mode race
    const connectTimeout = setTimeout(() => {
      if (!isActive) return;

      const wsUrl = `ws://localhost:8080/ws/terminal/${sessionId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isActive) return;
        onReadyRef.current?.();
      };

      ws.onmessage = (event) => {
        if (!isActive) return;
        const data = event.data;

        // Check for level complete marker
        if (data.includes("__LEVEL_COMPLETE__")) {
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
        term.writeln("\r\n\x1b[31mConnection error\x1b[0m");
      };

      ws.onclose = () => {
        if (!isActive) return;
        term.writeln("\r\n\x1b[33mDisconnected\x1b[0m");
      };

      // Send input to WebSocket
      term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(data);
        }
      });
    }, 100);

    // Handle resize
    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      isActive = false;
      clearTimeout(connectTimeout);
      window.removeEventListener("resize", handleResize);
      if (wsRef.current) {
        wsRef.current.close();
      }
      term.dispose();
    };
  }, [sessionId]); // Only depend on sessionId

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
