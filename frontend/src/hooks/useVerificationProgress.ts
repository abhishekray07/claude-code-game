import { useState, useEffect, useCallback, useRef } from "react";
import { config } from "../config";

interface VerificationRule {
  type: string;
  passed: boolean;
  path?: string;
  tool_name?: string;
  description?: string;
}

interface StepProgress {
  id: string;
  name: string;
  subtitle: string;
  passed: boolean;
  rules: VerificationRule[];
  passed_count: number;
  total_count: number;
}

export interface VerificationProgress {
  rules: VerificationRule[];
  completed: boolean;
  passed_count: number;
  total_count: number;
  steps?: StepProgress[];
  current_step?: number;
}

const POLL_INTERVAL = 3000; // 3 seconds

export function useVerificationProgress(sessionId: string | null) {
  const [progress, setProgress] = useState<VerificationProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  const fetchProgress = useCallback(async () => {
    if (!sessionId) return;

    try {
      const baseUrl = `${config.apiUrl}/api/sessions/${sessionId}/progress`;

      const response = await fetch(baseUrl);
      if (response.ok) {
        const data = await response.json();
        setProgress(data.progress);
        setError(null);
      } else {
        setError("Failed to fetch progress");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      setProgress(null);
      return;
    }

    setLoading(true);
    fetchProgress();

    // Poll for progress updates
    intervalRef.current = window.setInterval(fetchProgress, POLL_INTERVAL);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [sessionId, fetchProgress]);

  return { progress, loading, error, refetch: fetchProgress };
}

// Human-readable labels for verification types
export function getVerificationLabel(type: string, rule: VerificationRule): string {
  // Use custom description if provided
  if (rule.description) return rule.description;

  switch (type) {
    case "file_contains":
      return `Edit ${rule.path || "file"}`;
    case "file_exists":
      return `Create ${rule.path || "file"}`;
    case "min_user_messages":
      return "Send messages to Claude";
    case "tool_called":
      return `Use ${rule.tool_name || "tool"}`;
    case "commit_exists":
      return "Make a git commit";
    case "command_output":
      return "Run command successfully";
    case "file_changed":
      return `Modify ${rule.path || "file"}`;
    case "glob_exists":
      return "Create required files";
    case "home_glob_exists":
      return "Configure Claude settings";
    case "tool_called_with_path":
      return `Use ${rule.tool_name || "tool"} on specific file`;
    default:
      return type.replace(/_/g, " ");
  }
}
