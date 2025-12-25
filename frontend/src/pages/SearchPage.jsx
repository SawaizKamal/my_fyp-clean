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
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-purple-400">VideoShortener</h1>
          <div className="flex items-center gap-4">
            <span className="text-gray-400">Welcome, {user?.username}</span>
            <button
              onClick={() => navigate('/chat')}
              className="text-gray-400 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition"
            >
              Chat Assistant
            </button>
            <button
              onClick={() => navigate('/')}
              className="text-gray-400 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition"
            >
              Home
            </button>
            <button
              onClick={() => {
                logout();
                navigate('/');
              }}
              className="text-gray-400 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition"
            >
              Logout
            </button>
          </div>
        </div>

        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for YouTube videos..."
              className="flex-1 px-6 py-4 rounded-xl bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 text-lg"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-8 py-4 bg-purple-600 hover:bg-purple-700 rounded-xl font-semibold transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {error && (
          <div className="bg-red-500 bg-opacity-20 border border-red-500 text-red-300 px-6 py-4 rounded-xl mb-8">
            {error}
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
          <div className="text-center text-gray-500 text-xl mt-20">
            Enter a search query to find YouTube videos
          </div>
        )}
        
        {results.length === 0 && !loading && error && (
          <div className="text-center text-yellow-500 text-lg mt-20">
            <p className="mb-4">⚠️ YouTube API key not configured</p>
            <p className="text-sm text-gray-400">
              To search YouTube videos, please set the YOUTUBE_API_KEY environment variable.
              <br />
              Get your API key from: <a href="https://console.cloud.google.com" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:underline">Google Cloud Console</a>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default SearchPage;

