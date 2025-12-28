import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function RegisterPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validation
    if (password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);

    const result = await register(username, password, email || undefined);
    
    if (result.success) {
      navigate('/search');
    } else {
      setError(result.error || 'Registration failed. Please try again.');
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-4 relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 grid-overlay opacity-20"></div>
      <div className="absolute top-0 right-0 w-96 h-96 bg-[#ff00ff] opacity-10 blur-3xl animate-float"></div>
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-[#ff0040] opacity-10 blur-3xl animate-float" style={{ animationDelay: '1s' }}></div>
      
      <div className="max-w-md w-full glass-neon rounded-2xl p-8 border-2 relative z-10 animate-fade-in" style={{ boxShadow: '0 0 40px rgba(255, 0, 255, 0.3)' }}>
        <div className="text-center mb-8">
          <h1 className="text-5xl font-black neon-text-pink mb-2 font-mono uppercase tracking-wider animate-neon-glow">you-solution</h1>
          <div className="w-24 h-1 bg-gradient-to-r from-transparent via-[#ff00ff] to-transparent mx-auto mb-4"></div>
          <p className="text-gray-300 font-mono text-lg">> CREATE ACCOUNT</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="glass border-2 border-[#ff0040] text-[#ff0040] px-4 py-3 rounded-lg text-sm font-mono animate-slide-in-left" style={{ boxShadow: '0 0 20px rgba(255, 0, 64, 0.5)' }}>
              <span className="font-bold">> ERROR:</span> {error}
            </div>
          )}

          <div>
            <label htmlFor="username" className="block text-[#00ff41] text-sm font-bold mb-2 font-mono uppercase">
              > USERNAME *
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-lg bg-black/80 border-2 border-[#00ff41] text-[#00ff41] placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#00ff41] focus:border-[#00ff41] font-mono transition-all duration-300 focus:shadow-[0_0_20px_rgba(0,255,65,0.3)]"
              placeholder="Choose a username"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-[#ff00ff] text-sm font-bold mb-2 font-mono uppercase">
              > EMAIL (OPTIONAL)
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-black/80 border-2 border-[#ff00ff] text-[#ff00ff] placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#ff00ff] focus:border-[#ff00ff] font-mono transition-all duration-300 focus:shadow-[0_0_20px_rgba(255,0,255,0.3)]"
              placeholder="Enter your email"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-[#00ff41] text-sm font-bold mb-2 font-mono uppercase">
              > PASSWORD *
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-lg bg-black/80 border-2 border-[#00ff41] text-[#00ff41] placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#00ff41] focus:border-[#00ff41] font-mono transition-all duration-300 focus:shadow-[0_0_20px_rgba(0,255,65,0.3)]"
              placeholder="At least 6 characters"
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-[#ff00ff] text-sm font-bold mb-2 font-mono uppercase">
              > CONFIRM PASSWORD *
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-lg bg-black/80 border-2 border-[#ff00ff] text-[#ff00ff] placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#ff00ff] focus:border-[#ff00ff] font-mono transition-all duration-300 focus:shadow-[0_0_20px_rgba(255,0,255,0.3)]"
              placeholder="Confirm your password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-[#ff0040] via-[#ff00ff] to-[#00ff41] hover:from-[#ff00ff] hover:via-[#00ff41] hover:to-[#ff0040] text-black font-black py-4 px-6 rounded-lg transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none cyber-button font-mono text-lg uppercase tracking-wider"
            style={{ boxShadow: '0 0 30px rgba(255, 0, 64, 0.5), 0 0 60px rgba(255, 0, 255, 0.3)' }}
          >
            {loading ? '> CREATING ACCOUNT...' : '> SIGN UP'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-300 font-mono">
            > ALREADY HAVE AN ACCOUNT?{' '}
            <Link to="/login" className="text-[#00ff41] font-bold hover:text-[#ff00ff] hover:underline transition-colors">
              SIGN IN
            </Link>
          </p>
        </div>

        <div className="mt-4 text-center">
          <Link to="/" className="text-gray-400 text-sm hover:text-[#00ff41] font-mono transition-colors">
            < BACK TO HOME
          </Link>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;
