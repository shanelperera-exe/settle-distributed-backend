import React from 'react';
import { useTheme } from '../hooks/useTheme';
import { motion } from 'framer-motion';
import { FiSun, FiMoon, FiMonitor, FiSettings } from 'react-icons/fi';

const Settings: React.FC = () => {
  const { theme, setTheme } = useTheme();

  return (
    <div className="max-w-4xl space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3"
      >
        <div className="text-[var(--primary)]">
          <FiSettings size={48} />
        </div>
        <div>
          <h1 className="text-3xl font-light text-[var(--text)] tracking-tight">Settings</h1>
          <p className="text-[var(--text-muted)] text-sm font-medium mt-1 uppercase tracking-widest">Configure application preferences</p>
        </div>
      </motion.div>

      <div className="bg-[var(--surface-solid)] backdrop-blur-md border border-[var(--glass-border)] shadow-lg">
        <div className="p-6 border-b border-[var(--glass-border)]">
          <h3 className="text-xl font-light text-[var(--text)] tracking-tight mb-1">Appearance</h3>
          <p className="text-xs text-[var(--text-muted)] uppercase tracking-widest font-bold">Customize how the dashboard looks on your device.</p>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <button
              onClick={() => setTheme('light')}
              className={`flex flex-col items-center justify-center p-8 border transition-all duration-200 ${
                theme === 'light'
                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)] shadow-[0_0_15px_rgba(var(--primary-rgb),0.2)]'
                  : 'border-[var(--glass-border)] text-[var(--text-muted)] hover:border-[var(--text)] hover:text-[var(--text)] hover:bg-[var(--surface-sunken)]'
              }`}
            >
              <FiSun className="text-4xl mb-4" />
              <span className="text-sm font-bold uppercase tracking-wider">Light</span>
            </button>

            <button
              onClick={() => setTheme('dark')}
              className={`flex flex-col items-center justify-center p-8 border transition-all duration-200 ${
                theme === 'dark'
                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)] shadow-[0_0_15px_rgba(var(--primary-rgb),0.2)]'
                  : 'border-[var(--glass-border)] text-[var(--text-muted)] hover:border-[var(--text)] hover:text-[var(--text)] hover:bg-[var(--surface-sunken)]'
              }`}
            >
              <FiMoon className="text-4xl mb-4" />
              <span className="text-sm font-bold uppercase tracking-wider">Dark</span>
            </button>

            <button
              onClick={() => setTheme('system')}
              className={`flex flex-col items-center justify-center p-8 border transition-all duration-200 ${
                theme === 'system'
                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)] shadow-[0_0_15px_rgba(var(--primary-rgb),0.2)]'
                  : 'border-[var(--glass-border)] text-[var(--text-muted)] hover:border-[var(--text)] hover:text-[var(--text)] hover:bg-[var(--surface-sunken)]'
              }`}
            >
              <FiMonitor className="text-4xl mb-4" />
              <span className="text-sm font-bold uppercase tracking-wider">System</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
