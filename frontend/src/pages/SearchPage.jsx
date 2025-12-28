import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/config';
import VideoCard from '../components/VideoCard';

function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.get('/search', {
        params: { q: query, max_results: 12 }
      });
      setResults(response.data.results);
    } catch (err) {
      setError('Failed to search videos. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 grid-overlay opacity-20"></div>
      <div className="absolute top-0 left-0 w-96 h-96 bg-[#ff0040] opacity-5 blur-3xl animate-float"></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        <div className="flex items-center justify-between mb-8 animate-slide-in-left">
          <h1 className="text-4xl font-black neon-text-green font-mono uppercase tracking-wider animate-neon-glow">you-solution</h1>
          <div className="flex items-center gap-4">
            <span className="text-gray-300 font-mono text-sm">[ {user?.username} ]</span>
            <button
              onClick={() => navigate('/chat')}
              className="glass border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black px-4 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm uppercase"
            >
              > CHAT
            </button>
            <button
              onClick={() => navigate('/')}
              className="glass border border-[#ff00ff] text-[#ff00ff] hover:bg-[#ff00ff] hover:text-black px-4 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm uppercase"
            >
              > HOME
            </button>
            <button
              onClick={() => {
                logout();
                navigate('/');
              }}
              className="glass border border-[#ff0040] text-[#ff0040] hover:bg-[#ff0040] hover:text-black px-4 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm uppercase"
            >
              > LOGOUT
            </button>
          </div>
        </div>

        <form onSubmit={handleSearch} className="mb-8 animate-fade-in">
          <div className="flex gap-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for YouTube videos..."
              className="flex-1 px-6 py-4 rounded-xl bg-black/80 border-2 border-[#00ff41] text-[#00ff41] placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#00ff41] focus:border-[#00ff41] text-lg font-mono transition-all duration-300 focus:shadow-[0_0_20px_rgba(0,255,65,0.3)]"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-8 py-4 bg-gradient-to-r from-[#ff0040] to-[#ff00ff] hover:from-[#ff00ff] hover:to-[#00ff41] rounded-xl font-black transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed cyber-button font-mono text-lg uppercase tracking-wider transform hover:scale-105 disabled:transform-none"
              style={{ boxShadow: '0 0 20px rgba(255, 0, 64, 0.5)' }}
            >
              {loading ? '> SEARCHING...' : '> SEARCH'}
            </button>
          </div>
        </form>

        {error && (
          <div className="glass border-2 border-[#ff0040] text-[#ff0040] px-6 py-4 rounded-xl mb-8 animate-slide-in-left font-mono" style={{ boxShadow: '0 0 20px rgba(255, 0, 64, 0.5)' }}>
            <span className="font-bold">> ERROR:</span> {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {results.map((video) => (
            <VideoCard
              key={video.video_id}
              video={video}
              onClick={() => navigate(`/process/${video.video_id}`)}
            />
          ))}
        </div>

        {results.length === 0 && !loading && !error && (
          <div className="text-center text-gray-400 text-xl mt-20 font-mono animate-fade-in">
            > ENTER A SEARCH QUERY TO FIND YOUTUBE VIDEOS
          </div>
        )}
        
        {results.length === 0 && !loading && error && (
          <div className="text-center glass border-2 border-[#ff00ff] rounded-xl p-8 mt-20 max-w-2xl mx-auto animate-fade-in" style={{ boxShadow: '0 0 30px rgba(255, 0, 255, 0.3)' }}>
            <p className="mb-4 text-[#ff00ff] font-mono font-bold text-lg">⚠️ YOUTUBE API KEY NOT CONFIGURED</p>
            <p className="text-sm text-gray-300 font-mono">
              > To search YouTube videos, please set the YOUTUBE_API_KEY environment variable.
              <br />
              Get your API key from: <a href="https://console.cloud.google.com" target="_blank" rel="noopener noreferrer" className="text-[#00ff41] hover:text-[#ff00ff] hover:underline transition-colors font-bold">Google Cloud Console</a>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default SearchPage;

