/**
 * Version and Environment Configuration
 */

// Version info
export const VERSION = '1.0.0';
export const BUILD_DATE = '2025-09-05';

// Get environment from env variable or default to development
export const ENVIRONMENT = import.meta.env.VITE_ENVIRONMENT || 'development';

// Environment display settings
export const ENV_CONFIG = {
  development: {
    name: 'Development',
    color: '#f59e0b', // amber
    bgColor: '#fef3c7',
    icon: '🔧'
  },
  staging: {
    name: 'Staging',
    color: '#8b5cf6', // purple
    bgColor: '#ede9fe',
    icon: '🚧'
  },
  production: {
    name: 'Production',
    color: '#10b981', // green
    bgColor: '#d1fae5',
    icon: '✅'
  }
};

// Get current environment config
export const getCurrentEnvConfig = () => {
  return ENV_CONFIG[ENVIRONMENT as keyof typeof ENV_CONFIG] || ENV_CONFIG.development;
};

// Full version string
export const getVersionString = () => {
  const env = getCurrentEnvConfig();
  return `Version ${VERSION} - ${env.name}`;
};

// Short version string
export const getShortVersionString = () => {
  const env = getCurrentEnvConfig();
  return `v${VERSION} - ${env.name}`;
};