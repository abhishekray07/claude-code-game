import "./App.css";

import { useCallback, useEffect, useRef, useState } from "react";

import { Terminal } from "./components/Terminal";
import { VideoPlayer } from "./components/VideoPlayer";
import { useProgress } from "./hooks/useProgress";
import {
  useVerificationProgress,
  getVerificationLabel,
} from "./hooks/useVerificationProgress";
import { config } from "./config";

const TOTAL_LESSONS = 11; // Lessons 1-11
const STATUS_POLL_INTERVAL = 5000; // 5 seconds

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
  ttyd_url?: string; // Present for Fly.io mode
  // Docker mode fields
  port?: number;
  ttyd_token?: string;
}

type LessonPhase = "watch" | "exercise";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [accessCode, setAccessCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [levelComplete, setLevelComplete] = useState(false);
  const [phase, setPhase] = useState<LessonPhase>("watch");
  const [selectedLesson, setSelectedLesson] = useState(1);
  const { progress, markComplete } = useProgress();

  // Check terminal mode
  const isDockerMode = config.terminalMode === "docker";

  // Verification progress for current exercise
  const { progress: verificationProgress } = useVerificationProgress(
    phase === "exercise" ? session?.session_id ?? null : null
  );

  // Status polling
  const pollIntervalRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (sessionId: string, levelNumber: number) => {
      stopPolling();

      const poll = async () => {
        try {
          const statusUrl = isDockerMode
            ? `${config.apiUrl}/api/docker/sessions/${sessionId}/status`
            : `${config.apiUrl}/api/sessions/${sessionId}/status`;

          const response = await fetch(statusUrl);
          if (response.ok) {
            const data = await response.json();
            if (data.completed) {
              setLevelComplete(true);
              markComplete(levelNumber);
              stopPolling();
            }
          }
        } catch (e) {
          console.error("Status poll error:", e);
        }
      };

      // Poll immediately, then every 5 seconds
      poll();
      pollIntervalRef.current = window.setInterval(poll, STATUS_POLL_INTERVAL);
    },
    [stopPolling, markComplete]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const startGame = async (levelNumber: number = 1) => {
    setLoading(true);
    setError("");
    setLevelComplete(false);
    setPhase("watch");
    stopPolling();

    try {
      let data: Session;

      if (isDockerMode) {
        // Docker mode: use Docker-specific API
        const response = await fetch(`${config.apiUrl}/api/docker/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            level_number: levelNumber,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to start Docker session");
        }

        const dockerData = await response.json();
        // Transform Docker API response to match Session interface
        data = {
          session_id: dockerData.session_id,
          level: dockerData.level,
          port: dockerData.port,
          ttyd_token: dockerData.ttyd_token,
        };
      } else {
        // Default mode: use standard sessions API
        const response = await fetch(`${config.apiUrl}/api/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            level_number: levelNumber,
            access_code: accessCode,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to start session");
        }

        data = await response.json();
      }

      setSession(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const startExercise = () => {
    setPhase("exercise");
    if (session) {
      startPolling(session.session_id, session.level.number);
    }
  };

  const nextLevel = async () => {
    if (session && isDockerMode) {
      const nextLevelNum = session.level.number + 1;
      if (nextLevelNum <= TOTAL_LESSONS) {
        setLoading(true);
        setLevelComplete(false);
        setPhase("watch");
        stopPolling();

        try {
          const response = await fetch(
            `${config.apiUrl}/api/docker/sessions/${session.session_id}/level`,
            {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ level_number: nextLevelNum }),
            }
          );

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Failed to update level");
          }

          const data = await response.json();
          setSession({
            ...session,
            level: data.level,
            port: data.port,
            ttyd_token: data.ttyd_token,
          });
        } catch (e) {
          setError(e instanceof Error ? e.message : "Unknown error");
        } finally {
          setLoading(false);
        }
      } else {
        setSession(null);
        setLevelComplete(false);
      }
    } else {
      // Non-Docker mode: original behavior
      if (session) {
        const nextLevelNum = session.level.number + 1;
        if (nextLevelNum <= TOTAL_LESSONS) {
          startGame(nextLevelNum);
        } else {
          setSession(null);
          setLevelComplete(false);
        }
      }
    }
  };

  const endSession = async () => {
    if (session) {
      stopPolling();
      try {
        const endpoint = isDockerMode
          ? `${config.apiUrl}/api/docker/sessions/${session.session_id}`
          : `${config.apiUrl}/api/sessions/${session.session_id}`;
        await fetch(endpoint, {
          method: "DELETE",
        });
      } catch (e) {
        console.error("Error ending session:", e);
      }
      setSession(null);
      setLevelComplete(false);
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
            {!isDockerMode && (
              <input
                type="text"
                placeholder="Access code (if required)"
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && startGame(selectedLesson)}
              />
            )}
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
                disabled={loading}
              >
                {loading ? "Starting..." : "Start"}
              </button>
            </div>
          </div>

          {error && <p className="error">{error}</p>}

          <p className="hint">
            You'll authenticate via Claude CLI in the terminal.{" "}
            <a
              href="https://console.anthropic.com/settings/keys"
              target="_blank"
              rel="noopener noreferrer"
            >
              Get an API key here
            </a>{" "}
            if you don't have one.
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

  // Exercise Phase
  return (
    <div className="game-screen">
      <div className="sidebar">
        <div className="level-info">
          <span className="module-badge">{session.level.module}</span>
          <span className="level-badge">Lesson {session.level.number}</span>
          <h2>{session.level.title}</h2>
        </div>

        <div className="instructions">
          {session.level.intro && (
            <div className="intro" style={{whiteSpace: 'pre-line', marginBottom: '1rem'}}>
              {session.level.intro}
            </div>
          )}
          {session.level.exercise && (
            <p className="objective">
              <strong>Objective:</strong> {session.level.exercise.objective}
            </p>
          )}

          {/* Verification Progress Checklist */}
          {verificationProgress && verificationProgress.rules.length > 0 && (
            <div className="verification-progress">
              <h4>Progress</h4>
              <ul className="verification-checklist">
                {verificationProgress.rules.map((rule, index) => (
                  <li key={index} className={rule.passed ? "passed" : "pending"}>
                    <span className="check-icon">
                      {rule.passed ? "\u2713" : "\u25CB"}
                    </span>
                    <span className="check-label">
                      {getVerificationLabel(rule.type, rule)}
                    </span>
                  </li>
                ))}
              </ul>
              <div className="progress-summary">
                {verificationProgress.passed_count} of {verificationProgress.total_count} complete
              </div>
            </div>
          )}

          {levelComplete && (
            <div className="completion-message">
              <p>Nice work! You've completed this lesson's objective.</p>
            </div>
          )}
        </div>

        {session.level.video && (
          <button className="rewatch-btn" onClick={() => setPhase("watch")}>
            ↺ Rewatch Video
          </button>
        )}

        <button className="end-session-btn" onClick={endSession}>
          End Session
        </button>

        {levelComplete && (
          <div className="level-complete">
            <p>🎉 Lesson Complete!</p>
            <p className="exit-hint">
              Press <code>Ctrl+C</code> twice to exit Claude
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

      <div className="terminal-container">
        <Terminal
          sessionId={session.session_id}
          ttydUrl={session.ttyd_url}
          ttydPort={session.port}
          ttydToken={session.ttyd_token}
          onReady={() => console.log("Terminal ready")}
          onLevelComplete={() => {
            setLevelComplete(true);
            markComplete(session.level.number);
          }}
        />
      </div>
    </div>
  );
}

export default App;
