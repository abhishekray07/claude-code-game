import { useState, useCallback } from "react";
import type { VerificationProgress } from "../hooks/useVerificationProgress";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }).catch(() => {});
  }, [text]);

  return (
    <button className="copy-btn" onClick={handleCopy} title="Copy to clipboard">
      {copied ? (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      )}
    </button>
  );
}

import type { LevelStep } from "../types";

export function StepSidebar({
  steps,
  verificationProgress,
  levelComplete,
}: {
  steps: LevelStep[];
  verificationProgress: VerificationProgress | null;
  levelComplete: boolean;
}) {
  const currentStep = verificationProgress?.current_step ?? 0;
  const stepProgresses = verificationProgress?.steps ?? [];

  return (
    <div className="step-sidebar">
      {steps.map((step, index) => {
        const stepProgress = stepProgresses[index];
        const isPassed = stepProgress?.passed ?? false;
        const isCurrent = index === currentStep && !levelComplete;
        const isFuture = index > currentStep && !levelComplete;

        return (
          <div
            key={step.id}
            className={`step-item ${isPassed ? "passed" : ""} ${isCurrent ? "current" : ""} ${isFuture ? "future" : ""}`}
          >
            <div className="step-header">
              <span className="step-indicator">
                {isPassed ? "\u2713" : index + 1}
              </span>
              <div className="step-title">
                <span className="step-name">{step.name}</span>
                {step.subtitle && (
                  <span className="step-subtitle">{step.subtitle}</span>
                )}
              </div>
            </div>

            {isCurrent && (
              <div className="step-body">
                <p className="step-description">{step.description}</p>

                {step.guided_prompts.length > 0 && (
                  <div className="guided-prompts">
                    {step.guided_prompts.map((prompt, pi) => (
                      <div key={pi} className="guided-prompt">
                        <span className="prompt-label">{prompt.label}</span>
                        <div className="prompt-text-wrapper">
                          <code className="prompt-text">{prompt.text}</code>
                          <CopyButton text={prompt.text} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {stepProgress && stepProgress.rules.length > 0 && (
                  <ul className="step-checklist">
                    {stepProgress.rules.map((rule, ri) => (
                      <li key={ri} className={rule.passed ? "passed" : "pending"}>
                        <span className="check-icon">
                          {rule.passed ? "\u2713" : "\u25CB"}
                        </span>
                        <span className="check-label">
                          {rule.description || rule.type.replace(/_/g, " ")}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
