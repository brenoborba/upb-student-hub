import { createContext, useContext, useState, type ReactNode } from 'react';

import type { ApiConfig } from './api';

const STORAGE_KEY = 'upb-hub.config';
export const DEFAULT_BASE_URL = 'http://127.0.0.1:8000';

interface ConfigContextValue {
  config: ApiConfig;
  isConfigured: boolean;
  saveConfig: (config: ApiConfig) => void;
}

const ConfigContext = createContext<ConfigContextValue | null>(null);

function loadConfig(): ApiConfig {
  if (typeof window === 'undefined') {
    return { baseUrl: DEFAULT_BASE_URL, apiKey: '' };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<ApiConfig>;
      return {
        baseUrl: parsed.baseUrl || DEFAULT_BASE_URL,
        apiKey: parsed.apiKey || '',
      };
    }
  } catch {
    // fall through to defaults
  }
  return { baseUrl: DEFAULT_BASE_URL, apiKey: '' };
}

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<ApiConfig>(loadConfig);

  const saveConfig = (next: ApiConfig) => {
    setConfig(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    }
  };

  const value: ConfigContextValue = {
    config,
    isConfigured: config.baseUrl.trim().length > 0 && config.apiKey.trim().length > 0,
    saveConfig,
  };

  return <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>;
}

export function useConfig(): ConfigContextValue {
  const ctx = useContext(ConfigContext);
  if (!ctx) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return ctx;
}
