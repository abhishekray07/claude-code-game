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
