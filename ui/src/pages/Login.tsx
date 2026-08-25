import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FiUser, FiLock, FiArrowRight, FiShield } from 'react-icons/fi';

import LogoImg from '../assets/logos/settle_logo_primary.svg';
import LogoWordGreen from '../assets/logos/logo_word_green.svg';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await fetch('/api/v1/auth/login/access-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Invalid credentials');
      }

      const data = await response.json();
      login(data.access_token, { username: data.username, role: data.role });
      navigate('/');
    } catch (err) {
      setError('AUTHENTICATION FAILED. VERIFY CREDENTIALS.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)] relative overflow-hidden font-sans">
      
      {/* Grid Pattern Background to match brutalist style */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
           style={{ backgroundImage: 'linear-gradient(var(--text) 1px, transparent 1px), linear-gradient(90deg, var(--text) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-[460px] p-8 sm:p-12 border border-[var(--glass-border)] bg-[var(--surface)] z-10 rounded-none shadow-none relative"
      >
        {/* Top accent line */}
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[var(--primary)] to-transparent opacity-50"></div>

        <div className="flex flex-col items-center mb-10">
          <motion.div 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.3 }}
            className="w-16 h-16 border border-[var(--glass-border)] flex items-center justify-center mb-6 p-3 rounded-none bg-[var(--surface-sunken)]"
          >
            <img src={LogoImg} alt="Settle Logo Mark" className="w-full h-full object-contain" />
          </motion.div>
          
          <motion.img 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.3 }}
            src={LogoWordGreen} 
            alt="Settle" 
            className="h-6 object-contain mb-3" 
          />
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.3 }}
            className="text-[var(--text-muted)] text-[11px] font-bold tracking-widest mt-2 text-center uppercase"
          >
            SYSTEM ACCESS
          </motion.p>
        </div>

        {error && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="p-4 mb-8 border border-red-500/30 bg-red-500/10 text-red-400 text-sm flex items-center gap-3 rounded-none"
          >
            <FiShield className="w-5 h-5 shrink-0" />
            <span className="font-bold uppercase tracking-wider text-[10px]">{error}</span>
          </motion.div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3, duration: 0.3 }}
          >
            <label className="block text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] mb-2 ml-1">
              OPERATOR ID
            </label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[var(--text-muted)] group-focus-within:text-[var(--primary)] transition-colors">
                <FiUser size={16} />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-[var(--surface-sunken)] border border-[var(--glass-border)] rounded-none pl-12 pr-4 py-3.5 text-[var(--text)] text-sm focus:outline-none focus:border-[var(--primary)] focus:bg-[var(--surface-solid)] transition-colors placeholder:text-[var(--text-muted)]/40 font-mono"
                placeholder="admin"
                required
              />
            </div>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4, duration: 0.3 }}
          >
            <label className="block text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] mb-2 ml-1">
              SECURITY KEY
            </label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[var(--text-muted)] group-focus-within:text-[var(--primary)] transition-colors">
                <FiLock size={16} />
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[var(--surface-sunken)] border border-[var(--glass-border)] rounded-none pl-12 pr-4 py-3.5 text-[var(--text)] text-sm focus:outline-none focus:border-[var(--primary)] focus:bg-[var(--surface-solid)] transition-colors placeholder:text-[var(--text-muted)]/40 tracking-widest font-mono"
                placeholder="••••••••"
                required
              />
            </div>
          </motion.div>

          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.3 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={isLoading}
            className="w-full bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-[var(--background)] font-bold uppercase tracking-widest py-3.5 rounded-none transition-colors mt-8 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(8,185,107,0.2)] hover:shadow-[0_0_20px_rgba(8,185,107,0.4)]"
          >
            {isLoading ? (
              <span className="flex items-center gap-3">
                <div className="w-4 h-4 border-2 border-[var(--background)] border-t-transparent rounded-full animate-spin" />
                VERIFYING...
              </span>
            ) : (
              <>
                INITIALIZE SESSION
                <FiArrowRight size={16} />
              </>
            )}
          </motion.button>
        </form>
        
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.3 }}
          className="mt-10 pt-6 border-t border-[var(--glass-border)] text-center flex flex-col items-center gap-2"
        >
          <span className="text-[10px] uppercase tracking-widest font-bold text-[var(--text-muted)]/60">
            ACCESS MATRIX
          </span>
          <div className="flex items-center justify-center gap-3 text-[10px] text-[var(--text-muted)] font-mono uppercase bg-[var(--surface-sunken)] px-4 py-2 border border-[var(--glass-border)] rounded-none">
            <span>admin</span>
            <span className="w-1 h-1 rounded-none bg-[var(--glass-border)]" />
            <span>viewer</span>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default Login;
