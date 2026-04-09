import "./App.css";

import { useCallback, useEffect, useRef, useState } from "react";

import { Terminal } from "./components/Terminal";
import { VideoPlayer } from "./components/VideoPlayer";
import { StepSidebar } from "./components/StepSidebar";
import { useProgress } from "./hooks/useProgress";
import {
  useVerificationProgress,
  getVerificationLabel,
} from "./hooks/useVerificationProgress";
import { config } from "./config";
import type { LevelStep } from "./types";

const TOTAL_LESSONS = 11; // Advanced track (hidden for now)
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
  steps?: LevelStep[];
}

interface Session {
  session_id: string;
  ws_token: string;
  level: Level;
}

type LessonPhase = "watch" | "exercise";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [levelComplete, setLevelComplete] = useState(false);
  const [phase, setPhase] = useState<LessonPhase>("watch");
  const { progress, markComplete } = useProgress();

  // Save workspace state
  const [savedPath, setSavedPath] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Verification progress for current exercise
  const { progress: verificationProgress } = useVerificationProgress(
    phase === "exercise" ? session?.session_id ?? null : null
  );

  // Status polling
  const pollIntervalRef = useRef<number | null>(null);

  const isFirstRun = progress.completedLessons.length === 0;
  const isIntroLesson = session?.level.number === 0;

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
    setSavedPath(null);
    setPhase("watch");
    stopPolling();

    try {
      const urlParams = new URLSearchParams(window.location.search);
      const workspaceDir = urlParams.get("workspace");

      const response = await fetch(`${config.apiUrl}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          level_number: levelNumber,
          ...(workspaceDir ? { workspace_dir: workspaceDir } : {}),
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

  // Auto-start exercise for killer lesson (no video phase)
  useEffect(() => {
    if (isIntroLesson && phase === "watch" && session) {
      startExercise();
    }
  }, [isIntroLesson, phase, session]);

  const saveWorkspace = async () => {
    if (!session) return;
    setSaving(true);
    try {
      const response = await fetch(
        `${config.apiUrl}/api/sessions/${session.session_id}/save-workspace`,
        { method: "POST" }
      );
      if (response.ok) {
        const data = await response.json();
        setSavedPath(data.path);
      }
    } catch (e) {
      console.error("Save error:", e);
    } finally {
      setSaving(false);
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
    setSavedPath(null);
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
      setSavedPath(null);
    }
  };

  // First-run hero
  if (!session && isFirstRun) {
    return (
      <div className="start-screen">
        <div className="start-content">
          <h1>Build Your First App with AI</h1>
          <p className="subtitle">
            Zero to working app in 6 steps. You + Claude Code.
          </p>

          <div className="input-group">
            <button
              onClick={() => startGame(0)}
              disabled={loading}
            >
              {loading ? "Setting up..." : "Start Building"}
            </button>
          </div>

          {error && <p className="error">{error}</p>}

          {/* Advanced track link hidden for now */}
        </div>
      </div>
    );
  }

  // Lesson picker — for returning users
  if (!session) {
    return (
      <div className="start-screen">
        <div className="start-content">
          <h1>Claude Code Game</h1>
          <p className="subtitle">
            Learn Claude Code through interactive challenges
          </p>

          {/* Killer lesson card */}
          <div className="input-group" style={{ marginBottom: "1.5rem" }}>
            <button
              onClick={() => startGame(0)}
              disabled={loading}
            >
              {progress.completedLessons.includes(0)
                ? "Replay: Build an Expense Tracker"
                : "Build an Expense Tracker (20 min)"}
            </button>
          </div>

          {/* Advanced Track hidden for now */}
        </div>
      </div>
    );
  }

  // Watch Phase
  if (phase === "watch") {
    if (isIntroLesson) return null; // Will auto-transition via useEffect

    const videoUrl = session.level.video?.url;
    const hasVideo = videoUrl && /youtu\.be\/|youtube\.com\//.test(videoUrl);

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
          {!isIntroLesson && (
            <span className="level-badge">Lesson {session.level.number}</span>
          )}
          <h2>{session.level.title}</h2>
        </div>

        <div className="instructions">
          {/* Step-based sidebar for lessons with steps */}
          {session.level.steps && session.level.steps.length > 0 ? (
            <>
              <StepSidebar
                steps={session.level.steps}
                verificationProgress={verificationProgress}
                levelComplete={levelComplete}
              />

              {verificationProgress && (
                <div className="progress-summary">
                  Step {Math.min((verificationProgress.current_step ?? 0) + 1, session.level.steps.length)} of{" "}
                  {session.level.steps.length}
                </div>
              )}
            </>
          ) : (
            <>
              {/* Original flat sidebar for non-step lessons */}
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
            </>
          )}

          {/* Completion message — same for both layouts */}
          {levelComplete && (
            <div className="completion-message">
              {isIntroLesson ? (
                <>
                  <p>You built a real app with AI!</p>
                  {savedPath ? (
                    <p style={{ fontSize: "0.875rem", color: "#4ade80" }}>
                      Saved to: {savedPath}
                    </p>
                  ) : (
                    <button
                      onClick={saveWorkspace}
                      disabled={saving}
                      style={{ marginTop: "0.5rem" }}
                    >
                      {saving ? "Saving..." : "Save my code"}
                    </button>
                  )}
                </>
              ) : (
                <p>Nice work! You've completed this lesson's objective.</p>
              )}
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
            {isIntroLesson ? (
              <button onClick={() => { setSession(null); setLevelComplete(false); setSavedPath(null); }}>
                Done
              </button>
            ) : session.level.number < TOTAL_LESSONS ? (
              <button onClick={nextLevel}>Next Lesson →</button>
            ) : (
              <button onClick={() => setSession(null)}>
                All Done!
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
