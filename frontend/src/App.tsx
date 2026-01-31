import "./App.css";

import { useCallback, useState } from "react";

import { Terminal } from "./components/Terminal";
import { VideoPlayer } from "./components/VideoPlayer";
import { useProgress } from "./hooks/useProgress";

const TOTAL_LESSONS = 9;

interface Video {
  url: string;
  duration_seconds: number;
}

interface Exercise {
  intro: string;
  objective: string;
}

interface Level {
  number: number;
  title: string;
  module: string;
  intro?: string;
  video?: Video;
  exercise?: Exercise;
}

interface Session {
  session_id: string;
  level: Level;
}

type LessonPhase = "watch" | "exercise";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [apiKey, setApiKey] = useState(import.meta.env.VITE_ANTHROPIC_API_KEY || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [levelComplete, setLevelComplete] = useState(false);
  const [phase, setPhase] = useState<LessonPhase>("watch");
  const [selectedLesson, setSelectedLesson] = useState(1);
  const { progress, markComplete } = useProgress();

  const startGame = async (levelNumber: number = 1) => {
    if (!apiKey.trim()) {
      setError("Please enter your API key");
      return;
    }

    setLoading(true);
    setError("");
    setLevelComplete(false);
    setPhase("watch");

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
    if (session) {
      markComplete(session.level.number);
    }
  }, [session, markComplete]);

  const startExercise = () => {
    setPhase("exercise");
  };

  const nextLevel = () => {
    if (session) {
      const nextLevelNum = session.level.number + 1;
      if (nextLevelNum <= TOTAL_LESSONS) {
        startGame(nextLevelNum);
      } else {
        // Course complete!
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
              onKeyDown={(e) => e.key === "Enter" && startGame(selectedLesson)}
            />
            <div className="lesson-select-row">
              <select
                value={selectedLesson}
                onChange={(e) => setSelectedLesson(Number(e.target.value))}
                className="lesson-select"
              >
                {Array.from({ length: TOTAL_LESSONS }, (_, i) => i + 1).map(
                  (n) => (
                    <option key={n} value={n}>
                      Lesson {n}
                    </option>
                  )
                )}
              </select>
              <button
                onClick={() => startGame(selectedLesson)}
                disabled={loading || !apiKey.trim()}
              >
                {loading ? "Starting..." : "Start"}
              </button>
            </div>
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

          <div className="progress-indicator">
            <span>
              {progress.completedLessons.length} of {TOTAL_LESSONS} lessons
              complete
            </span>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${(progress.completedLessons.length / TOTAL_LESSONS) * 100}%`,
                }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Watch Phase
  if (phase === "watch") {
    const hasVideo = session.level.video?.url;

    return (
      <div className="lesson-screen">
        <div className="lesson-header">
          <span className="module-badge">{session.level.module}</span>
          <h1>
            Lesson {session.level.number}: {session.level.title}
          </h1>
        </div>

        <div className="lesson-content">
          {hasVideo ? (
            <>
              <VideoPlayer url={session.level.video!.url} onEnded={() => {}} />
              <button className="start-exercise-btn" onClick={startExercise}>
                Start Exercise →
              </button>
            </>
          ) : (
            <>
              <div className="no-video-message">
                <p>This lesson doesn't have a video yet.</p>
                <p>Proceed directly to the exercise.</p>
              </div>
              <button className="start-exercise-btn" onClick={startExercise}>
                Start Exercise →
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  // Exercise Phase (Game screen)
  return (
    <div className="game-screen">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="level-info">
          <span className="module-badge">{session.level.module}</span>
          <span className="level-badge">Lesson {session.level.number}</span>
          <h2>{session.level.title}</h2>
        </div>

        <div className="instructions">
          {session.level.exercise ? (
            <>
              <p>{session.level.exercise.intro}</p>
              <p className="objective">
                <strong>Objective:</strong> {session.level.exercise.objective}
              </p>
            </>
          ) : (
            <>
              <p>
                Claude Code is an AI coding assistant that lives in your
                terminal.
              </p>
              <p className="action">
                👉 Type <code>claude</code> to start
              </p>
            </>
          )}
          {session.level.intro && (
            <div className="step-by-step">
              <h3>Instructions</h3>
              <pre>{session.level.intro}</pre>
            </div>
          )}
          {levelComplete && (
            <div className="completion-message">
              <p>Nice work! You've completed this lesson's objective.</p>
            </div>
          )}
        </div>

        <div className="commands">
          <h3>Commands</h3>
          <ul>
            <li>
              <code>/hint</code> - Get a hint
            </li>
            <li>
              <code>/skip</code> - Skip this lesson
            </li>
            <li>
              <code>/objective</code> - Show objective
            </li>
            <li>
              <code>/progress</code> - Check progress
            </li>
          </ul>
        </div>

        {session.level.video && (
          <button className="rewatch-btn" onClick={() => setPhase("watch")}>
            ↺ Rewatch Video
          </button>
        )}

        {levelComplete && (
          <div className="level-complete">
            <p>🎉 Lesson Complete!</p>
            <p className="exit-hint">
              Press <code>Esc</code> twice to exit Claude
            </p>
            {session.level.number < TOTAL_LESSONS ? (
              <button onClick={nextLevel}>Next Lesson →</button>
            ) : (
              <button onClick={() => setSession(null)}>
                🏆 Course Complete!
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
