import type { VerificationProgress } from "../hooks/useVerificationProgress";

interface GuidedPrompt {
  text: string;
  label: string;
}

interface LevelStep {
  id: string;
  name: string;
  subtitle: string;
  description: string;
  guided_prompts: GuidedPrompt[];
}

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
                        <code className="prompt-text">{prompt.text}</code>
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
