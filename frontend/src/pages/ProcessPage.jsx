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
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 grid-overlay opacity-20"></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        <button
          onClick={() => navigate('/search')}
          className="glass border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black px-4 py-2 rounded-lg mb-6 transition-all duration-300 cyber-button font-mono text-sm uppercase"
        >
          < BACK TO SEARCH
        </button>

        <div className="max-w-4xl mx-auto animate-fade-in">
          <h1 className="text-4xl font-black neon-text-green mb-8 font-mono uppercase tracking-wider animate-neon-glow">> PROCESS VIDEO</h1>

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
          <form onSubmit={handleSubmit} className="glass-neon rounded-xl p-8 border-2">
            <label htmlFor="goal" className="block text-xl font-black text-[#00ff41] mb-4 font-mono uppercase">
              > WHAT PART OF THIS VIDEO WOULD YOU LIKE TO EXTRACT?
            </label>
            <textarea
              id="goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g., Show me the tutorial steps for building a website..."
              rows="4"
              className="w-full px-6 py-4 rounded-lg bg-black/80 border-2 border-[#ff00ff] text-[#00ff41] placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#ff00ff] focus:border-[#ff00ff] mb-6 font-mono transition-all duration-300 focus:shadow-[0_0_20px_rgba(255,0,255,0.3)]"
            />

            {error && (
              <div className="glass border-2 border-[#ff0040] text-[#ff0040] px-4 py-3 rounded-lg mb-6 font-mono animate-slide-in-left" style={{ boxShadow: '0 0 20px rgba(255, 0, 64, 0.5)' }}>
                <span className="font-bold">> ERROR:</span> {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !goal.trim()}
              className="w-full py-5 bg-gradient-to-r from-[#ff0040] via-[#ff00ff] to-[#00ff41] hover:from-[#ff00ff] hover:via-[#00ff41] hover:to-[#ff0040] rounded-lg font-black transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed text-lg cyber-button font-mono uppercase tracking-wider transform hover:scale-105 disabled:transform-none"
              style={{ boxShadow: '0 0 30px rgba(255, 0, 64, 0.5), 0 0 60px rgba(255, 0, 255, 0.3)' }}
            >
              {loading ? '> PROCESSING...' : '> PROCESS VIDEO →'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default ProcessPage;

