// Terminal mode: 'docker' | 'modal' | 'fly' | 'local'
export const TERMINAL_MODE = import.meta.env.VITE_TERMINAL_MODE || 'docker';
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const config = {
  apiUrl: API_URL,
  terminalMode: TERMINAL_MODE,
};
