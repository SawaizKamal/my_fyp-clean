import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/config';

function ResultPage() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const pollStatus = setInterval(async () => {
      try {
        const response = await api.get(`/status/${taskId}`);
        setStatus(response.data);

        // If completed or failed, stop polling
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(pollStatus);
          setLoading(false);
        }
      } catch (err) {
        console.error('Failed to get status:', err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollStatus);
  }, [taskId]);

  const getStatusText = () => {
    switch (status?.status) {
      case 'pending':
        return 'Waiting to start...';
      case 'downloading':
        return 'Downloading video...';
      case 'transcribing':
        return 'Transcribing audio...';
      case 'filtering':
        return 'AI is finding relevant segments...';
      case 'compiling':
        return 'Compiling your video...';
      case 'completed':
        return 'Completed!';
      case 'failed':
        return 'Failed to process';
      default:
        return 'Initializing...';
    }
  };

  const getStatusColor = () => {
    switch (status?.status) {
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-blue-500';
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
          <h1 className="text-4xl font-black neon-text-green mb-8 font-mono uppercase tracking-wider animate-neon-glow">> PROCESSING STATUS</h1>

          {loading && status && (
            <div className="glass-neon rounded-xl p-8 mb-8 border-2 animate-fade-in">
              <div className="mb-4">
                <div className="flex items-center mb-2">
                  <div className={`w-4 h-4 rounded-full ${getStatusColor() === 'bg-green-500' ? 'bg-[#00ff41]' : getStatusColor() === 'bg-red-500' ? 'bg-[#ff0040]' : 'bg-[#ff00ff]'} mr-3 animate-pulse`} style={{ boxShadow: `0 0 10px ${getStatusColor() === 'bg-green-500' ? '#00ff41' : getStatusColor() === 'bg-red-500' ? '#ff0040' : '#ff00ff'}` }}></div>
                  <p className="text-xl font-mono font-bold text-[#00ff41]">{getStatusText().toUpperCase()}</p>
                </div>
              </div>

              {status.status !== 'completed' && status.status !== 'failed' && (
                <div className="w-full bg-black/80 rounded-full h-3 border-2 border-[#00ff41] overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-[#ff0040] via-[#ff00ff] to-[#00ff41] h-full rounded-full transition-all duration-300 relative" 
                    style={{ width: `${status.progress || 0}%`, boxShadow: '0 0 20px rgba(255, 0, 255, 0.8)' }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-scan-line"></div>
                  </div>
                </div>
              )}
              {status.progress !== undefined && (
                <p className="text-sm text-[#ff00ff] mt-3 font-mono font-bold">{status.progress}% COMPLETE</p>
              )}
            </div>
          )}

          {status?.status === 'completed' && (
            <div className="glass-neon rounded-xl p-8 border-2 animate-fade-in" style={{ boxShadow: '0 0 30px rgba(0, 255, 65, 0.3)' }}>
              <div className="mb-6">
                <h2 className="text-3xl font-black neon-text-green mb-4 font-mono uppercase tracking-wider">
                  ✅ YOUR VIDEO IS READY!
                </h2>
              </div>

              <video
                controls
                className="w-full rounded-lg mb-6 border-2 border-[#00ff41]"
                src={`/api/video/${taskId}`}
              >
                Your browser does not support the video tag.
              </video>

              <div className="flex gap-4">
                <a
                  href={`/api/video/${taskId}`}
                  download
                  className="flex-1 py-4 px-6 glass border-2 border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black rounded-lg text-center font-black transition-all duration-300 cyber-button font-mono uppercase tracking-wider"
                >
                  > DOWNLOAD VIDEO
                </a>
                <button
                  onClick={() => navigate('/search')}
                  className="flex-1 py-4 px-6 glass border-2 border-[#ff00ff] text-[#ff00ff] hover:bg-[#ff00ff] hover:text-black rounded-lg font-black transition-all duration-300 cyber-button font-mono uppercase tracking-wider"
                >
                  > PROCESS ANOTHER
                </button>
              </div>
            </div>
          )}

          {status?.status === 'failed' && (
            <div className="glass border-2 border-[#ff0040] rounded-xl p-8 animate-fade-in" style={{ boxShadow: '0 0 30px rgba(255, 0, 64, 0.5)' }}>
              <h2 className="text-3xl font-black neon-text-red mb-4 font-mono uppercase tracking-wider">
                ❌ PROCESSING FAILED
              </h2>
              <p className="text-gray-300 mb-6 font-mono">
                > {status.error || 'An error occurred during processing'}
              </p>
              <button
                onClick={() => navigate('/search')}
                className="py-4 px-8 glass border-2 border-[#ff00ff] text-[#ff00ff] hover:bg-[#ff00ff] hover:text-black rounded-lg font-black transition-all duration-300 cyber-button font-mono uppercase tracking-wider"
              >
                > TRY AGAIN
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ResultPage;

