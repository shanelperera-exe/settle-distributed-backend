import React from 'react';
import { useTheme } from '../hooks/useTheme';
import { FiSun, FiMoon, FiMonitor } from 'react-icons/fi';

const Settings: React.FC = () => {
  const { theme, setTheme } = useTheme();

  return (
    <div className="max-w-4xl">
      <h2 className="text-2xl font-google-code font-bold mb-6 tracking-tight">Settings</h2>

      <div className="bg-[var(--surface)] border border-gray-200 dark:border-gray-800 rounded-none overflow-hidden shadow-none">
        <div className="p-6 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-lg font-google-code font-bold mb-1">Appearance</h3>
          <p className="text-sm text-gray-500 font-google-code">Customize how the dashboard looks on your device.</p>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <button
              onClick={() => setTheme('light')}
              className={`flex flex-col items-center justify-center p-6 rounded-none border-2 transition-colors ${
                theme === 'light'
                  ? 'border-[var(--primary)] bg-[var(--primary)]/5 text-[var(--primary)]'
                  : 'border-gray-200 dark:border-gray-800 text-gray-500 hover:border-gray-300 dark:hover:border-gray-700'
              }`}
            >
              <FiSun className="text-3xl mb-3" />
              <span className="font-google-code font-bold">Light</span>
            </button>

            <button
              onClick={() => setTheme('dark')}
              className={`flex flex-col items-center justify-center p-6 rounded-none border-2 transition-colors ${
                theme === 'dark'
                  ? 'border-[var(--primary)] bg-[var(--primary)]/5 text-[var(--primary)]'
                  : 'border-gray-200 dark:border-gray-800 text-gray-500 hover:border-gray-300 dark:hover:border-gray-700'
              }`}
            >
              <FiMoon className="text-3xl mb-3" />
              <span className="font-google-code font-bold">Dark</span>
            </button>

            <button
              onClick={() => setTheme('system')}
              className={`flex flex-col items-center justify-center p-6 rounded-none border-2 transition-colors ${
                theme === 'system'
                  ? 'border-[var(--primary)] bg-[var(--primary)]/5 text-[var(--primary)]'
                  : 'border-gray-200 dark:border-gray-800 text-gray-500 hover:border-gray-300 dark:hover:border-gray-700'
              }`}
            >
              <FiMonitor className="text-3xl mb-3" />
              <span className="font-google-code font-bold">System</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
