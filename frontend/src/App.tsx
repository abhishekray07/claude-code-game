import "./App.css";

import { useCallback, useState } from "react";

import { Terminal } from "./components/Terminal";

interface Level {
  number: number;
  title: string;
  module: string;
  intro?: string;
}

interface Session {
  session_id: string;
  level: Level;
}

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [levelComplete, setLevelComplete] = useState(false);

  const startGame = async (levelNumber: number = 1) => {
    if (!apiKey.trim()) {
      setError("Please enter your API key");
      return;
    }

    setLoading(true);
    setError("");
    setLevelComplete(false);

    try {
      const response = await fetch("http://localhost:8080/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, level_number: levelNumber }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to start session");
      }

      const data = await response.json();
      setSession(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleLevelComplete = useCallback(() => {
    setLevelComplete(true);
  }, []);

  const nextLevel = () => {
    if (session) {
      const nextLevelNum = session.level.number + 1;
      if (nextLevelNum <= 4) {
        startGame(nextLevelNum);
      } else {
        // Game complete!
        setSession(null);
        setLevelComplete(false);
      }
    }
  };

  // Start screen
  if (!session) {
    return (
      <div className="start-screen">
        <div className="start-content">
          <h1>Claude Code Game</h1>
          <p className="subtitle">
            Learn Claude Code through interactive challenges
          </p>

          <div className="input-group">
            <input
              type="password"
              placeholder="Enter your Anthropic API key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && startGame(1)}
            />
            <button
              onClick={() => startGame(1)}
              disabled={loading || !apiKey.trim()}
            >
              {loading ? "Starting..." : "Start Game"}
            </button>
          </div>

          {error && <p className="error">{error}</p>}

          <p className="hint">
            Don't have an API key?{" "}
            <a
              href="https://console.anthropic.com/settings/keys"
              target="_blank"
              rel="noopener noreferrer"
            >
              Get one here
            </a>
          </p>
        </div>
      </div>
    );
  }

  // Game screen
  return (
    <div className="game-screen">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="level-info">
          <span className="module-badge">{session.level.module}</span>
          <span className="level-badge">Level {session.level.number}</span>
          <h2>{session.level.title}</h2>
        </div>

        <div className="instructions">
          {!levelComplete ? (
            <>
              <p>
                Claude Code is an AI coding assistant that lives in your
                terminal.
              </p>
              <p className="action">
                👉 Type <code>claude</code> to start
              </p>
            </>
          ) : (
            <>
              <p>Nice work! You've completed this level's objective.</p>
              <p className="action">
                👉 Click <strong>Next Level</strong> below to continue
              </p>
            </>
          )}
        </div>

        <div className="commands">
          <h3>Commands</h3>
          <ul>
            <li>
              <code>/hint</code> - Get a hint
            </li>
            <li>
              <code>/skip</code> - Skip this level
            </li>
            <li>
              <code>/objective</code> - Show objective
            </li>
            <li>
              <code>/progress</code> - Check progress
            </li>
          </ul>
        </div>

        {levelComplete && (
          <div className="level-complete">
            <p>🎉 Level Complete!</p>
            <p className="exit-hint">
              Press <code>Esc</code> twice to exit Claude
            </p>
            {session.level.number < 4 ? (
              <button onClick={nextLevel}>Next Level →</button>
            ) : (
              <button onClick={() => setSession(null)}>
                🏆 Game Complete!
              </button>
            )}
          </div>
        )}
      </div>

      {/* Terminal */}
      <div className="terminal-container">
        <Terminal
          sessionId={session.session_id}
          onLevelComplete={handleLevelComplete}
        />
      </div>
    </div>
  );
}

export default App;
