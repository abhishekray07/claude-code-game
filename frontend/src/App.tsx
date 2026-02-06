import "./App.css";

import { useCallback, useEffect, useRef, useState } from "react";

import { Terminal } from "./components/Terminal";
import { VideoPlayer } from "./components/VideoPlayer";
import { useAuth } from "./hooks/useAuth";
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
  ws_token: string;
  level: Level;
}

type LessonPhase = "watch" | "exercise";

function App() {
  const { auth, loading: authLoading, requestCode, confirmCode, continueAsGuest, logout } = useAuth();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [levelComplete, setLevelComplete] = useState(false);
  const [phase, setPhase] = useState<LessonPhase>("watch");
  const [selectedLesson, setSelectedLesson] = useState(1);
  const { progress, markComplete } = useProgress();

  // Auth screen state
  const [authEmail, setAuthEmail] = useState("");
  const [authCode, setAuthCode] = useState("");
  const [authStep, setAuthStep] = useState<"email" | "code">("email");
  const [authError, setAuthError] = useState("");
  const [authSubmitting, setAuthSubmitting] = useState(false);

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
          const response = await fetch(
            `${config.apiUrl}/api/sessions/${sessionId}/status`
          );
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
      const response = await fetch(`${config.apiUrl}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          level_number: levelNumber,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to start session");
      }

      const data: Session = await response.json();
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
    if (!session) return;

    const nextLevelNum = session.level.number + 1;
    if (nextLevelNum > TOTAL_LESSONS) {
      setSession(null);
      setLevelComplete(false);
      return;
    }

    setLoading(true);
    setLevelComplete(false);
    setPhase("watch");
    stopPolling();

    try {
      const response = await fetch(
        `${config.apiUrl}/api/sessions/${session.session_id}/level`,
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
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const endSession = async () => {
    if (session) {
      stopPolling();
      try {
        await fetch(
          `${config.apiUrl}/api/sessions/${session.session_id}`,
          { method: "DELETE" }
        );
      } catch (e) {
        console.error("Error ending session:", e);
      }
      setSession(null);
      setLevelComplete(false);
    }
  };

  // Auth loading screen
  if (authLoading) {
    return (
      <div className="start-screen">
        <div className="start-content">
          <h1>Claude Code Game</h1>
          <p className="subtitle">Loading...</p>
        </div>
      </div>
    );
  }

  // Auth screen — shown when not authenticated and not guest
  if (!auth.token && !auth.guest) {
    const handleRequestCode = async () => {
      setAuthError("");
      setAuthSubmitting(true);
      try {
        await requestCode(authEmail);
        setAuthStep("code");
      } catch (e) {
        setAuthError(e instanceof Error ? e.message : "Failed to send code");
      } finally {
        setAuthSubmitting(false);
      }
    };

    const handleConfirmCode = async () => {
      setAuthError("");
      setAuthSubmitting(true);
      try {
        await confirmCode(authEmail, authCode);
      } catch (e) {
        setAuthError(e instanceof Error ? e.message : "Invalid code");
      } finally {
        setAuthSubmitting(false);
      }
    };

    return (
      <div className="start-screen">
        <div className="start-content">
          <h1>Claude Code Game</h1>
          <p className="subtitle">
            Sign in to track your progress on the leaderboard
          </p>

          <div className="input-group">
            {authStep === "email" ? (
              <>
                <input
                  type="email"
                  placeholder="Enter your email"
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !authSubmitting && handleRequestCode()}
                />
                <button onClick={handleRequestCode} disabled={authSubmitting || !authEmail}>
                  {authSubmitting ? "Sending..." : "Send Code"}
                </button>
              </>
            ) : (
              <>
                <p style={{ color: "#888", fontSize: "0.875rem", margin: 0 }}>
                  Code sent to {authEmail}
                </p>
                <input
                  type="text"
                  placeholder="Enter verification code"
                  value={authCode}
                  onChange={(e) => setAuthCode(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !authSubmitting && handleConfirmCode()}
                />
                <button onClick={handleConfirmCode} disabled={authSubmitting || !authCode}>
                  {authSubmitting ? "Verifying..." : "Verify"}
                </button>
                <button
                  onClick={() => { setAuthStep("email"); setAuthCode(""); setAuthError(""); }}
                  style={{ background: "transparent", border: "1px solid #444", color: "#888" }}
                >
                  Back
                </button>
              </>
            )}
          </div>

          {authError && <p className="error">{authError}</p>}

          <p className="hint">
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); continueAsGuest(); }}
            >
              Continue as Guest
            </a>
          </p>
        </div>
      </div>
    );
  }

  // Start screen
  if (!session) {
    return (
      <div className="start-screen">
        <div className="start-content">
          <h1>Claude Code Game</h1>
          <p className="subtitle">
            Learn Claude Code through interactive challenges
          </p>

          {auth.guest && (
            <p className="guest-banner">
              Playing as guest — progress won't be saved to leaderboard
            </p>
          )}

          <div className="input-group">
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

          {auth.token && (
            <p className="hint">
              Signed in as {auth.email}{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); logout(); }}>
                Sign out
              </a>
            </p>
          )}
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
            <p>Lesson Complete!</p>
            <p className="exit-hint">
              Press <code>Ctrl+C</code> twice to exit Claude
            </p>
            {session.level.number < TOTAL_LESSONS ? (
              <button onClick={nextLevel}>Next Lesson →</button>
            ) : (
              <button onClick={() => setSession(null)}>
                Course Complete!
              </button>
            )}
          </div>
        )}
      </div>

      <div className="terminal-container">
        <Terminal
          sessionId={session.session_id}
          wsToken={session.ws_token}
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
