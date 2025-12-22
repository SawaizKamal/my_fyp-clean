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
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <button
          onClick={() => navigate('/search')}
          className="text-gray-400 hover:text-white mb-6"
        >
          ← Back to Search
        </button>

        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Processing Status</h1>

          {loading && status && (
            <div className="bg-gray-800 rounded-xl p-8 mb-8">
              <div className="mb-4">
                <div className="flex items-center mb-2">
                  <div className={`w-3 h-3 rounded-full ${getStatusColor()} mr-3 animate-pulse`}></div>
                  <p className="text-xl">{getStatusText()}</p>
                </div>
              </div>

              {status.status !== 'completed' && status.status !== 'failed' && (
                <div className="w-full bg-gray-700 rounded-full h-2.5">
                  <div className="bg-purple-600 h-2.5 rounded-full animate-progress" style={{ width: '50%' }}></div>
                </div>
              )}
            </div>
          )}

          {status?.status === 'completed' && (
            <div className="bg-gray-800 rounded-xl p-8">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-green-400 mb-4">
                  ✅ Your video is ready!
                </h2>
              </div>

              <video
                controls
                className="w-full rounded-lg mb-6"
                src={`http://localhost:8000/api/video/${taskId}`}
              >
                Your browser does not support the video tag.
              </video>

              <div className="flex gap-4">
                <a
                  href={`http://localhost:8000/api/video/${taskId}`}
                  download
                  className="flex-1 py-3 px-6 bg-green-600 hover:bg-green-700 rounded-lg text-center font-semibold transition duration-200"
                >
                  Download Video
                </a>
                <button
                  onClick={() => navigate('/search')}
                  className="flex-1 py-3 px-6 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold transition duration-200"
                >
                  Process Another
                </button>
              </div>
            </div>
          )}

          {status?.status === 'failed' && (
            <div className="bg-red-500 bg-opacity-20 border border-red-500 rounded-xl p-8">
              <h2 className="text-2xl font-bold text-red-400 mb-4">
                ❌ Processing Failed
              </h2>
              <p className="text-gray-300 mb-6">
                {status.error || 'An error occurred during processing'}
              </p>
              <button
                onClick={() => navigate('/search')}
                className="py-3 px-6 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold transition duration-200"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ResultPage;

