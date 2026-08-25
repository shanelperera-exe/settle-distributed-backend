import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FiEye, FiEyeOff } from 'react-icons/fi';
import LogoImg from '../assets/logos/settle_logo_primary.svg';
import LoginVideo from '../assets/videos/login_screen_vid.mp4';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
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
    <main className="text-[var(--text)] bg-[var(--background)]" style={{ fontFamily: "'Codec Pro', sans-serif" }}>
      <section className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
        
        {/* Top Left Logo */}
        <div className="absolute top-10 left-10 md:left-12 z-20 flex items-center gap-3">
          <img src={LogoImg} alt="Settle Logo Mark" className="h-16 w-16 object-contain shrink-0" />
          <div className="flex flex-col justify-center font-bold uppercase tracking-tighter text-[32px] leading-[0.85] text-[var(--text)]">
            <span>Developer</span>
            <span>Console</span>
          </div>
        </div>

        {/* Left Form Area */}
        <div className="flex items-center justify-start pb-4 pt-32 px-8 md:pl-20 lg:pl-32 bg-[var(--background)] z-10 relative">
          <div className="w-full max-w-xl">
            <h1 className="mb-3 text-left text-5xl font-semibold tracking-tight text-[var(--text)]">Access settle <br/>&lt;Developer Console/&gt;</h1>
            <p className="mb-10 text-left text-lg text-[var(--text-muted)]">Welcome back! Please enter your details</p>

            {error && (
              <div className="mb-6 p-4 bg-red-500/10 text-red-500 text-sm rounded-lg border border-red-500/20">
                {error}
              </div>
            )}

            <form className="w-full space-y-6" onSubmit={handleSubmit}>
              <div className="w-full text-left">
                <label htmlFor="email-input" className="mb-2 inline-block text-base font-medium text-[var(--text)]">Username<span className="text-red-500 ml-1">*</span></label>
                <input 
                  id="email-input" 
                  type="text"
                  placeholder="Enter your username" 
                  className="w-full rounded-none border border-[var(--glass-border)] bg-[var(--surface)] text-[var(--text)] px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50 focus:border-[var(--primary)] transition-colors placeholder:text-[var(--text-muted)]/50 text-lg" 
                  required 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>

              <div className="w-full text-left">
                <label htmlFor="password-input" className="mb-2 inline-block text-base font-medium text-[var(--text)]">Password<span className="text-red-500 ml-1">*</span></label>
                <div className="relative">
                  <input 
                    id="password-input" 
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password" 
                    className="w-full rounded-none border border-[var(--glass-border)] bg-[var(--surface)] text-[var(--text)] px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50 focus:border-[var(--primary)] transition-colors placeholder:text-[var(--text-muted)]/50 text-lg" 
                    required 
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button 
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text)] transition-colors focus:outline-none"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <FiEyeOff size={20} /> : <FiEye size={20} />}
                  </button>
                </div>
              </div>

              <button disabled={isLoading} type="submit" className="mt-8 w-full rounded-none bg-[var(--primary)] hover:brightness-90 px-6 py-4 text-center text-lg font-bold text-[var(--background)] transition-all disabled:opacity-50">
                {isLoading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>
          </div>
        </div>

        {/* Right Video Area */}
        <div className="group sticky top-0 h-80 overflow-hidden rounded-none bg-[var(--secondary)] lg:h-screen">
          <video 
            autoPlay 
            loop 
            muted 
            playsInline
            src={LoginVideo} 
            className="h-full w-full object-cover" 
          />
        </div>
      </section>
    </main>
  );
};

export default Login;
