export interface GuidedPrompt {
  text: string;
  label: string;
}

export interface LevelStep {
  id: string;
  name: string;
  subtitle: string;
  description: string;
  guided_prompts: GuidedPrompt[];
}
