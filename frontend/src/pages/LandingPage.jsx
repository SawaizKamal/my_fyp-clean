import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  const handleGetStarted = () => {
    if (isAuthenticated) {
      navigate('/search');
    } else {
      navigate('/login');
    }
  };

  return (
    <div className="min-h-screen bg-black relative overflow-hidden">
      {/* Animated background grid */}
      <div className="absolute inset-0 grid-overlay opacity-30"></div>
      
      {/* Animated scan line effect */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute w-full h-1 bg-gradient-to-r from-transparent via-[#00ff41] to-transparent opacity-50 animate-scan-line"></div>
      </div>

      {/* Neon corner accents */}
      <div className="absolute top-0 left-0 w-64 h-64 bg-[#ff0040] opacity-10 blur-3xl animate-float"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-[#ff00ff] opacity-10 blur-3xl animate-float" style={{ animationDelay: '1s' }}></div>
      <div className="absolute top-1/2 right-0 w-48 h-48 bg-[#00ff41] opacity-10 blur-3xl animate-float" style={{ animationDelay: '2s' }}></div>

      <div className="container mx-auto px-4 py-16 relative z-10">
        {/* Navigation Bar */}
        <div className="flex justify-between items-center mb-12 animate-slide-in-left">
          <h2 className="text-3xl font-bold neon-text-green animate-neon-glow">
            you-solution
          </h2>
          <div className="flex gap-4">
            {isAuthenticated ? (
              <>
                <span className="text-gray-300 font-mono">[ {user?.username} ]</span>
                <button
                  onClick={() => navigate('/search')}
                  className="glass-neon text-[#00ff41] px-6 py-2 rounded-lg hover:bg-[#00ff41] hover:text-black transition-all duration-300 cyber-button font-mono text-sm border border-[#00ff41]"
                >
                  > DASHBOARD
                </button>
                <button
                  onClick={logout}
                  className="glass text-[#ff0040] px-6 py-2 rounded-lg hover:bg-[#ff0040] hover:text-black transition-all duration-300 cyber-button font-mono text-sm border border-[#ff0040]"
                >
                  > LOGOUT
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => navigate('/login')}
                  className="glass text-[#00ff41] px-6 py-2 rounded-lg hover:bg-[#00ff41] hover:text-black transition-all duration-300 cyber-button font-mono text-sm border border-[#00ff41]"
                >
                  > LOGIN
                </button>
                <button
                  onClick={() => navigate('/register')}
                  className="glass-neon text-[#ff00ff] px-6 py-2 rounded-lg hover:bg-[#ff00ff] hover:text-black transition-all duration-300 cyber-button font-mono text-sm border border-[#ff00ff] animate-neon-pulse"
                >
                  > SIGN UP
                </button>
              </>
            )}
          </div>
        </div>

        <div className="max-w-5xl mx-auto text-center text-white animate-fade-in">
          <div className="mb-8">
            <h1 className="text-8xl font-black mb-6 neon-text-green animate-neon-glow" style={{ 
              fontFamily: 'monospace',
              letterSpacing: '0.1em',
              textTransform: 'uppercase'
            }}>
              you-solution
            </h1>
            <div className="w-32 h-1 bg-gradient-to-r from-transparent via-[#00ff41] to-transparent mx-auto mb-6"></div>
          </div>
          
          <p className="text-3xl mb-6 text-gray-200 font-light" style={{ letterSpacing: '0.05em' }}>
            > EXTRACT WHAT MATTERS
          </p>
          <p className="text-xl mb-12 text-gray-400 font-mono">
            AI-POWERED VIDEO INTELLIGENCE SYSTEM
          </p>
          
          <button
            onClick={handleGetStarted}
            className="relative px-12 py-5 bg-gradient-to-r from-[#ff0040] via-[#ff00ff] to-[#00ff41] text-black font-black text-xl rounded-lg transition-all duration-300 transform hover:scale-110 cyber-button animate-neon-pulse"
            style={{ 
              fontFamily: 'monospace',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              boxShadow: '0 0 30px rgba(255, 0, 64, 0.5), 0 0 60px rgba(255, 0, 255, 0.3), 0 0 90px rgba(0, 255, 65, 0.2)'
            }}
          >
            {isAuthenticated ? '> ACCESS DASHBOARD' : '> INITIALIZE SYSTEM'}
            <span className="ml-2">→</span>
          </button>
        </div>

        <div className="max-w-6xl mx-auto mt-32 grid md:grid-cols-3 gap-8 animate-slide-in-right">
          <div className="glass-neon rounded-xl p-8 text-white border border-[#00ff41] hover:border-[#ff00ff] transition-all duration-300 group">
            <div className="text-5xl mb-4 group-hover:scale-110 transition-transform duration-300">🎯</div>
            <h3 className="text-2xl font-bold mb-4 neon-text-green group-hover:neon-text-pink transition-all duration-300" style={{ fontFamily: 'monospace' }}>
              > SMART EXTRACTION
            </h3>
            <p className="text-gray-300 leading-relaxed">
              Neural network algorithms identify and extract critical solution segments from video content
            </p>
            <div className="mt-4 h-1 bg-gradient-to-r from-[#00ff41] to-transparent"></div>
          </div>

          <div className="glass rounded-xl p-8 text-white border border-[#ff00ff] hover:border-[#ff0040] transition-all duration-300 group">
            <div className="text-5xl mb-4 group-hover:scale-110 transition-transform duration-300">⚡</div>
            <h3 className="text-2xl font-bold mb-4 neon-text-pink group-hover:neon-text-red transition-all duration-300" style={{ fontFamily: 'monospace' }}>
              > QUANTUM PROCESSING
            </h3>
            <p className="text-gray-300 leading-relaxed">
              Real-time transcription and analysis with sub-second response times
            </p>
            <div className="mt-4 h-1 bg-gradient-to-r from-[#ff00ff] to-transparent"></div>
          </div>

          <div className="glass-neon rounded-xl p-8 text-white border border-[#ff0040] hover:border-[#00ff41] transition-all duration-300 group">
            <div className="text-5xl mb-4 group-hover:scale-110 transition-transform duration-300">📱</div>
            <h3 className="text-2xl font-bold mb-4 neon-text-red group-hover:neon-text-green transition-all duration-300" style={{ fontFamily: 'monospace' }}>
              > INTUITIVE INTERFACE
            </h3>
            <p className="text-gray-300 leading-relaxed">
              Zero-learning-curve design optimized for maximum efficiency
            </p>
            <div className="mt-4 h-1 bg-gradient-to-r from-[#ff0040] to-transparent"></div>
          </div>
        </div>

        {/* Debug info panel (futuristic style) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="max-w-4xl mx-auto mt-16 glass border border-[#00ff41] rounded-xl p-6 animate-fade-in">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-[#00ff41] font-mono text-sm">> DEBUG MODE ACTIVE</span>
              <div className="flex-1 h-px bg-gradient-to-r from-[#00ff41] to-transparent"></div>
            </div>
            <div className="font-mono text-xs text-gray-400 space-y-1">
              <div>> System Status: <span className="text-[#00ff41]">OPERATIONAL</span></div>
              <div>> Authentication: <span className={isAuthenticated ? "text-[#00ff41]" : "text-[#ff0040]"}>{isAuthenticated ? "AUTHENTICATED" : "UNAUTHENTICATED"}</span></div>
              <div>> User Session: <span className="text-[#00ff41]">{user?.username || "NONE"}</span></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default LandingPage;

