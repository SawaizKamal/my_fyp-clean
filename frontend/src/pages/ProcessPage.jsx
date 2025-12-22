import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/config';

function ProcessPage() {
  const { videoId } = useParams();
  const navigate = useNavigate();
  const [goal, setGoal] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!goal.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/process', {
        video_id: videoId,
        goal: goal
      });

      // Navigate to result page with task_id
      navigate(`/result/${response.data.task_id}`);
    } catch (err) {
      setError('Failed to start processing. Please try again.');
      console.error(err);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <button
          onClick={() => navigate('/search')}
          className="text-gray-400 hover:text-white mb-6"
        >
          ← Back to Search
        </button>

        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Process Video</h1>

          {/* YouTube Embed */}
          <div className="mb-8 bg-black rounded-xl overflow-hidden">
            <iframe
              width="100%"
              height="500"
              src={`https://www.youtube.com/embed/${videoId}`}
              title="YouTube video player"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              className="w-full"
            ></iframe>
          </div>

          {/* Goal Input Form */}
          <form onSubmit={handleSubmit} className="bg-gray-800 rounded-xl p-8">
            <label htmlFor="goal" className="block text-xl font-semibold mb-4">
              What part of this video would you like to extract?
            </label>
            <textarea
              id="goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g., Show me the tutorial steps for building a website..."
              rows="4"
              className="w-full px-6 py-4 rounded-lg bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 mb-6"
            />

            {error && (
              <div className="bg-red-500 bg-opacity-20 border border-red-500 text-red-300 px-4 py-3 rounded-lg mb-6">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !goal.trim()}
              className="w-full py-4 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-lg"
            >
              {loading ? 'Processing...' : 'Process Video →'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default ProcessPage;

