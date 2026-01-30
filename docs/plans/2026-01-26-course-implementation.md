# Course Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the game into a paid course with video lessons + interactive exercises.

**Architecture:** Extend existing level schema with video support, add Watch→Exercise phase UI, track user progress via localStorage.

**Tech Stack:** React 19, FastAPI, react-player (video), existing xterm.js terminal.

---

## Task 1: Extend Level Schema with Video Field

**Files:**
- Modify: `backend/app/models/level.py`

**Step 1: Add Video and Exercise models to level.py**

```python
class Video(BaseModel):
    """Video configuration for a lesson."""
    url: str
    duration_seconds: int


class Exercise(BaseModel):
    """Exercise configuration for a lesson."""
    intro: str
    objective: str


class Level(BaseModel):
    """A game level definition."""
    id: str
    number: int
    title: str
    module: str
    intro: str
    video: Video | None = None  # Optional for backwards compatibility
    exercise: Exercise | None = None  # Optional for backwards compatibility
    verification: list[VerificationRule]
    hints: list[Hint] = []
    success: str
    limits: LevelLimits = LevelLimits()
```

**Step 2: Verify schema loads existing levels**

Run: `cd backend && python -c "from app.services.levels import list_levels; print(list_levels())"`
Expected: List of 4 levels without errors

**Step 3: Commit**

```bash
git add backend/app/models/level.py
git commit -m "feat: add video and exercise fields to level schema"
```

---

## Task 2: Add New Verification Types

**Files:**
- Modify: `backend/app/models/level.py`
- Modify: `backend/app/services/verification.py`

**Step 1: Add COMMIT_EXISTS and COMMAND_OUTPUT to VerificationType enum**

In `backend/app/models/level.py`:

```python
class VerificationType(str, Enum):
    """Types of verification checks."""
    MESSAGE_EXISTS = "message_exists"
    TOOL_CALLED = "tool_called"
    FILE_EXISTS = "file_exists"
    FILE_CONTAINS = "file_contains"
    FILE_CHANGED = "file_changed"
    COMMIT_EXISTS = "commit_exists"      # New
    COMMAND_OUTPUT = "command_output"    # New
```

**Step 2: Add fields to VerificationRule for new types**

```python
class VerificationRule(BaseModel):
    """A single verification rule."""
    type: VerificationType
    tool_name: str | None = None  # For TOOL_CALLED
    path: str | None = None  # For FILE_* checks
    pattern: str | None = None  # For FILE_CONTAINS, COMMIT_EXISTS (message pattern)
    command: str | None = None  # For COMMAND_OUTPUT
    expected_output: str | None = None  # For COMMAND_OUTPUT (regex pattern)
```

**Step 3: Implement verification methods in verification.py**

Add to `VerificationEngine._check_rule`:

```python
elif rule.type == VerificationType.COMMIT_EXISTS:
    return await self._check_commit_exists(rule.pattern)
elif rule.type == VerificationType.COMMAND_OUTPUT:
    return await self._check_command_output(rule.command, rule.expected_output)
```

Add new methods:

```python
async def _check_commit_exists(self, pattern: str | None) -> bool:
    """Check if a git commit exists (optionally matching message pattern)."""
    if not self.sandbox.workspace_dir:
        return False

    stdout, stderr, returncode = await self.sandbox.exec_command(
        "git", "log", "--oneline", "-n", "10"
    )
    if returncode != 0:
        return False

    if pattern:
        return bool(re.search(pattern, stdout, re.IGNORECASE))
    return bool(stdout.strip())  # Any commit exists

async def _check_command_output(self, command: str | None, expected: str | None) -> bool:
    """Check if command output matches expected pattern."""
    if not command:
        return False

    # Split command into args
    import shlex
    args = shlex.split(command)

    stdout, stderr, returncode = await self.sandbox.exec_command(*args)

    if expected:
        return bool(re.search(expected, stdout + stderr))
    return returncode == 0  # Just check success
```

**Step 4: Test new verification types manually**

Run: `cd backend && python -c "from app.models.level import VerificationType; print([v.value for v in VerificationType])"`
Expected: `['message_exists', 'tool_called', 'file_exists', 'file_contains', 'file_changed', 'commit_exists', 'command_output']`

**Step 5: Commit**

```bash
git add backend/app/models/level.py backend/app/services/verification.py
git commit -m "feat: add commit_exists and command_output verification types"
```

---

## Task 3: Add Video Player to Frontend

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/components/VideoPlayer.tsx`
- Create: `frontend/src/components/VideoPlayer.css`

**Step 1: Install react-player**

Run: `cd frontend && npm install react-player`

**Step 2: Create VideoPlayer component**

Create `frontend/src/components/VideoPlayer.tsx`:

```tsx
import ReactPlayer from "react-player";
import "./VideoPlayer.css";

interface VideoPlayerProps {
  url: string;
  onEnded?: () => void;
  onReady?: () => void;
}

export function VideoPlayer({ url, onEnded, onReady }: VideoPlayerProps) {
  return (
    <div className="video-player-container">
      <ReactPlayer
        url={url}
        width="100%"
        height="100%"
        controls
        onEnded={onEnded}
        onReady={onReady}
        config={{
          vimeo: {
            playerOptions: {
              byline: false,
              portrait: false,
              title: false,
            },
          },
        }}
      />
    </div>
  );
}
```

**Step 3: Create VideoPlayer styles**

Create `frontend/src/components/VideoPlayer.css`:

```css
.video-player-container {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
}
```

**Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/VideoPlayer.tsx frontend/src/components/VideoPlayer.css
git commit -m "feat: add VideoPlayer component with react-player"
```

---

## Task 4: Update Level Interface and API Response

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `backend/app/main.py`

**Step 1: Update TypeScript Level interface**

In `frontend/src/App.tsx`, update the interface:

```tsx
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
```

**Step 2: Update backend to include video in session response**

In `backend/app/main.py`, update the session response (find the route that returns level data and ensure it includes the video field - Pydantic will serialize it automatically).

**Step 3: Commit**

```bash
git add frontend/src/App.tsx backend/app/main.py
git commit -m "feat: add video and exercise to level interface"
```

---

## Task 5: Implement Watch → Exercise Phase Transition

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

**Step 1: Add phase state to App**

Add new state and phase logic:

```tsx
type LessonPhase = "watch" | "exercise";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [levelComplete, setLevelComplete] = useState(false);
  const [phase, setPhase] = useState<LessonPhase>("watch");  // New

  const startGame = async (levelNumber: number = 1) => {
    // ... existing code ...
    setPhase("watch");  // Reset phase when starting new level
  };

  const startExercise = () => {
    setPhase("exercise");
  };

  // ... rest of component
}
```

**Step 2: Create Watch phase UI**

Add watch phase rendering (before the terminal section):

```tsx
// Watch Phase
if (session && phase === "watch") {
  const hasVideo = session.level.video?.url;

  return (
    <div className="lesson-screen">
      <div className="lesson-header">
        <span className="module-badge">{session.level.module}</span>
        <h1>Lesson {session.level.number}: {session.level.title}</h1>
      </div>

      <div className="lesson-content">
        {hasVideo ? (
          <>
            <VideoPlayer
              url={session.level.video!.url}
              onEnded={() => {}}
            />
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
```

**Step 3: Update exercise phase to show "Rewatch Video" button**

In the sidebar during exercise phase, add:

```tsx
{session.level.video && (
  <button className="rewatch-btn" onClick={() => setPhase("watch")}>
    ↺ Rewatch Video
  </button>
)}
```

**Step 4: Add CSS for lesson screen**

Add to `frontend/src/App.css`:

```css
/* Lesson Screen (Watch Phase) */
.lesson-screen {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #0f0f1a;
  color: #fff;
  padding: 40px;
}

.lesson-header {
  text-align: center;
  margin-bottom: 32px;
}

.lesson-header h1 {
  font-size: 1.8rem;
  margin-top: 12px;
}

.lesson-content {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.start-exercise-btn {
  padding: 14px 32px;
  border-radius: 8px;
  border: none;
  background: #6366f1;
  color: #fff;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.start-exercise-btn:hover {
  background: #4f46e5;
  transform: translateY(-2px);
}

.no-video-message {
  text-align: center;
  color: #888;
  padding: 40px;
}

.rewatch-btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid #444;
  background: transparent;
  color: #888;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.rewatch-btn:hover {
  border-color: #6366f1;
  color: #fff;
}
```

**Step 5: Import VideoPlayer in App.tsx**

```tsx
import { VideoPlayer } from "./components/VideoPlayer";
```

**Step 6: Test the UI flow**

Run: `cd frontend && npm run dev`
Expected: UI shows watch phase, clicking "Start Exercise" shows terminal

**Step 7: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.css
git commit -m "feat: implement watch to exercise phase transition"
```

---

## Task 6: Add Course Progress Tracking

**Files:**
- Create: `frontend/src/hooks/useProgress.ts`
- Modify: `frontend/src/App.tsx`

**Step 1: Create progress hook**

Create `frontend/src/hooks/useProgress.ts`:

```tsx
import { useState, useEffect } from "react";

const STORAGE_KEY = "claude-course-progress";

interface Progress {
  completedLessons: number[];
  currentLesson: number;
}

export function useProgress() {
  const [progress, setProgress] = useState<Progress>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return { completedLessons: [], currentLesson: 1 };
      }
    }
    return { completedLessons: [], currentLesson: 1 };
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  }, [progress]);

  const markComplete = (lessonNumber: number) => {
    setProgress((prev) => ({
      completedLessons: [...new Set([...prev.completedLessons, lessonNumber])],
      currentLesson: Math.max(prev.currentLesson, lessonNumber + 1),
    }));
  };

  const resetProgress = () => {
    setProgress({ completedLessons: [], currentLesson: 1 });
  };

  return { progress, markComplete, resetProgress };
}
```

**Step 2: Integrate progress hook in App**

In `frontend/src/App.tsx`:

```tsx
import { useProgress } from "./hooks/useProgress";

function App() {
  const { progress, markComplete, resetProgress } = useProgress();

  // Update handleLevelComplete to track progress
  const handleLevelComplete = useCallback(() => {
    setLevelComplete(true);
    if (session) {
      markComplete(session.level.number);
    }
  }, [session, markComplete]);

  // ... rest of component
}
```

**Step 3: Add progress indicator to start screen**

In start screen section:

```tsx
<div className="progress-indicator">
  <span>{progress.completedLessons.length} of 12 lessons complete</span>
  <div className="progress-bar">
    <div
      className="progress-fill"
      style={{ width: `${(progress.completedLessons.length / 12) * 100}%` }}
    />
  </div>
</div>
```

**Step 4: Add progress CSS**

```css
.progress-indicator {
  margin-top: 2rem;
  width: 100%;
}

.progress-indicator span {
  font-size: 0.875rem;
  color: #888;
}

.progress-bar {
  height: 4px;
  background: #333;
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  transition: width 0.3s ease;
}
```

**Step 5: Commit**

```bash
git add frontend/src/hooks/useProgress.ts frontend/src/App.tsx frontend/src/App.css
git commit -m "feat: add course progress tracking with localStorage"
```

---

## Task 7: Create Lesson Directory Structure

**Files:**
- Create: `levels/01-context-is-everything/lesson.yaml`
- Create: `levels/01-context-is-everything/exercise/` (copy from starter-app)
- Create lessons 02-12 directories

**Step 1: Create new directory structure**

```bash
mkdir -p levels/01-context-is-everything/exercise
mkdir -p levels/02-first-bug-fix/exercise
mkdir -p levels/03-claude-md/exercise
mkdir -p levels/04-monitor-manage/exercise
mkdir -p levels/05-spec-driven/exercise
mkdir -p levels/06-planning-mode/exercise
mkdir -p levels/07-testing-debugging/exercise
mkdir -p levels/08-git-integration/exercise
mkdir -p levels/09-skills/exercise
mkdir -p levels/10-mcp-servers/exercise
mkdir -p levels/11-parallel-work/exercise
mkdir -p levels/12-hooks-safety/exercise
```

**Step 2: Create lesson 1 YAML**

Create `levels/01-context-is-everything/lesson.yaml`:

```yaml
id: "context-is-everything"
number: 1
module: "Mental Model"
title: "Context is Everything"

video:
  url: "https://vimeo.com/placeholder"  # Replace with actual video
  duration_seconds: 240

exercise:
  intro: |
    Now try it yourself. You have a simple todo app in front of you.
    Ask Claude to explain what it does.
  objective: "Have a conversation with Claude about the codebase"

intro: |
  ╔══════════════════════════════════════════════════════════════╗
  ║  LESSON 1: Context is Everything                              ║
  ╚══════════════════════════════════════════════════════════════╝

  Welcome! You're about to meet Claude Code, an AI coding assistant
  that lives in your terminal.

  In front of you is a simple todo app. Let's have Claude help us
  understand the code.

  👉 Type: claude

  Then ask Claude to explain what this app does.

verification:
  - type: message_exists

hints:
  - after_minutes: 1
    text: "💡 Hint: Just type 'claude' and press Enter to start!"
  - after_minutes: 3
    text: "💡 Hint: Try asking Claude 'what does this todo app do?'"

success: |
  ✅ Great! You just had your first conversation with Claude Code.

  Notice how Claude read the files to understand the code before responding.
  That's context in action!

limits:
  max_duration_minutes: 10
  max_claude_messages: 10
```

**Step 3: Copy starter-app files to lesson 1 exercise folder**

```bash
cp levels/starter-app/* levels/01-context-is-everything/exercise/
```

**Step 4: Commit**

```bash
git add levels/
git commit -m "feat: create lesson directory structure for 12-lesson course"
```

---

## Task 8: Update Level Loader for New Structure

**Files:**
- Modify: `backend/app/services/levels.py`

**Step 1: Update load_level to support both structures**

The level loader should look for `lesson.yaml` in numbered directories first, falling back to `definitions/` for backwards compatibility:

```python
def load_level(level_number: int) -> Level | None:
    """Load a level by number."""
    levels_dir = Path(__file__).parent.parent.parent.parent / "levels"

    # Try new structure first: levels/01-*/lesson.yaml
    for dir_path in levels_dir.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(f"{level_number:02d}-"):
            lesson_file = dir_path / "lesson.yaml"
            if lesson_file.exists():
                return _parse_level(lesson_file)

    # Fallback to old structure: levels/definitions/0X-*.yaml
    definitions_dir = levels_dir / "definitions"
    if definitions_dir.exists():
        for yaml_file in definitions_dir.glob(f"{level_number:02d}-*.yaml"):
            return _parse_level(yaml_file)

    return None
```

**Step 2: Add helper to get exercise directory**

```python
def get_exercise_dir(level_number: int) -> Path | None:
    """Get the exercise directory for a level."""
    levels_dir = Path(__file__).parent.parent.parent.parent / "levels"

    # Try new structure: levels/01-*/exercise/
    for dir_path in levels_dir.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(f"{level_number:02d}-"):
            exercise_dir = dir_path / "exercise"
            if exercise_dir.exists():
                return exercise_dir

    # Fallback to shared starter-app
    starter_app = levels_dir / "starter-app"
    if starter_app.exists():
        return starter_app

    return None
```

**Step 3: Commit**

```bash
git add backend/app/services/levels.py
git commit -m "feat: update level loader to support new lesson directory structure"
```

---

## Task 9: Update Sandbox to Use Per-Lesson Exercise Files

**Files:**
- Modify: `backend/app/api/terminal.py`

**Step 1: Update session creation to copy level-specific exercise files**

Find where starter-app files are copied and update to use `get_exercise_dir`:

```python
from app.services.levels import get_exercise_dir

# In session creation:
exercise_dir = get_exercise_dir(level.number)
if exercise_dir:
    # Copy exercise files to workspace
    for file in exercise_dir.iterdir():
        if file.is_file():
            shutil.copy(file, sandbox.workspace_dir / file.name)
```

**Step 2: Commit**

```bash
git add backend/app/api/terminal.py
git commit -m "feat: copy level-specific exercise files to sandbox"
```

---

## Task 10: Create Remaining Lesson YAMLs

**Files:**
- Create: `levels/02-first-bug-fix/lesson.yaml` through `levels/12-hooks-safety/lesson.yaml`

**Step 1: Create lesson 2 - First Bug Fix**

Create `levels/02-first-bug-fix/lesson.yaml`:

```yaml
id: "first-bug-fix"
number: 2
module: "Mental Model"
title: "Your First Bug Fix"

video:
  url: "https://vimeo.com/placeholder"
  duration_seconds: 300

exercise:
  intro: |
    The todo app has a bug - tasks show the wrong text.
    Tell Claude to fix it and verify the fix works.
  objective: "Have Claude fix the bug and verify it works"

intro: |
  ╔══════════════════════════════════════════════════════════════╗
  ║  LESSON 2: Your First Bug Fix                                 ║
  ╚══════════════════════════════════════════════════════════════╝

  The todo app has a bug. When you add a task, something's not right.

  Watch how Claude reads the code, identifies the bug, and fixes it.

  👉 Type: claude

  Then tell Claude: "There's a bug in the todo app. Can you find and fix it?"

verification:
  - type: tool_called
    tool_name: Edit
  - type: file_contains
    path: todo.py
    pattern: 'self\.text'

hints:
  - after_minutes: 2
    text: "💡 Hint: Ask Claude to look at the todo app and find the bug"
  - after_minutes: 4
    text: "💡 Hint: The bug is in how tasks are displayed - 'title' vs 'text'"

success: |
  ✅ Bug fixed! You saw the Read → Edit → Verify workflow.

  Claude read the code, identified the issue (title vs text),
  and made the fix. This is the core loop you'll use constantly.

limits:
  max_duration_minutes: 15
  max_claude_messages: 20
```

**Step 2: Create lessons 3-12** (abbreviated - follow same pattern)

Each lesson follows the curriculum from the design doc. Key verification rules:

- Lesson 3 (CLAUDE.md): `file_exists: CLAUDE.md`
- Lesson 5 (Spec-Driven): `file_exists: spec.md`, `file_contains: todo.py: due_date`
- Lesson 7 (Testing): `command_output: pytest: PASSED`
- Lesson 8 (Git): `commit_exists: .*`
- Lesson 9 (Skills): `file_exists: .claude/skills/lint.md`

**Step 3: Commit**

```bash
git add levels/
git commit -m "feat: add lesson YAML files for all 12 lessons"
```

---

## Task 11: Wire Up Complete Flow

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `backend/app/main.py`

**Step 1: Update total lessons constant**

In `frontend/src/App.tsx`:

```tsx
const TOTAL_LESSONS = 12;
```

Update `nextLevel` logic:

```tsx
if (nextLevelNum <= TOTAL_LESSONS) {
```

**Step 2: Add API endpoint to get total lessons**

In `backend/app/main.py`:

```python
@app.get("/api/lessons/count")
async def get_lesson_count():
    """Get total number of lessons."""
    from app.services.levels import list_levels
    levels = list_levels()
    return {"total": len(levels)}
```

**Step 3: Commit**

```bash
git add frontend/src/App.tsx backend/app/main.py
git commit -m "feat: support dynamic lesson count"
```

---

## Task 12: Final Integration Test

**Step 1: Start backend**

Run: `cd backend && uv run uvicorn app.main:app --reload --port 8080`
Expected: Server starts on port 8080

**Step 2: Start frontend**

Run: `cd frontend && npm run dev`
Expected: Dev server starts

**Step 3: Manual test flow**

1. Enter API key
2. See "0 of 12 lessons complete"
3. Click Start
4. See watch phase (with placeholder video message)
5. Click "Start Exercise"
6. See terminal
7. Complete exercise
8. Click "Next Lesson"
9. Verify progress updates

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete course implementation with video support"
```

---

## Summary

This plan transforms the game into a 12-lesson course with:

1. **Video support** in lesson schema
2. **Watch → Exercise** phase transition
3. **Progress tracking** via localStorage
4. **New verification types**: `commit_exists`, `command_output`
5. **Per-lesson exercise files** in new directory structure
6. **12 lesson YAMLs** following the curriculum

Total: ~12 tasks, each completable in 5-15 minutes.
