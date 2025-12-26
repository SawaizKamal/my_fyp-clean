import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/config';

function VideoPlayerPage() {
  const { videoId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const videoRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [highlightedSegment, setHighlightedSegment] = useState(null);

  useEffect(() => {
    if (!videoId) {
      setError('Video ID is required');
      setLoading(false);
      return;
    }

    const loadVideo = async () => {
      try {
        setLoading(true);
        setError(null);

        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7b7349a8-4aec-40c0-88c1-85a8567508ca',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'VideoPlayerPage.jsx:25',message:'Before API call',data:{videoId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'FRONTEND'})}).catch(()=>{});
        // #endregion

        // Call transcription API
        const response = await api.post(`/video/transcribe/${videoId}`);
        
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7b7349a8-4aec-40c0-88c1-85a8567508ca',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'VideoPlayerPage.jsx:30',message:'API call succeeded',data:{hasData:!!response.data},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'FRONTEND'})}).catch(()=>{});
        // #endregion
        
        setTranscript(response.data);
      } catch (err) {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7b7349a8-4aec-40c0-88c1-85a8567508ca',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'VideoPlayerPage.jsx:33',message:'API call failed',data:{error:err.message,status:err.response?.status,detail:err.response?.data?.detail},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'FRONTEND'})}).catch(()=>{});
        // #endregion
        setError(err.response?.data?.detail || 'Failed to load video transcription. Please try again.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadVideo();
  }, [videoId]);

  // Update current time from video player
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const updateTime = () => {
      setCurrentTime(video.currentTime);
    };

    video.addEventListener('timeupdate', updateTime);
    return () => video.removeEventListener('timeupdate', updateTime);
  }, [transcript]);

  const jumpToTimestamp = (startTime) => {
    if (transcript.video_unavailable && transcript.youtube_embed_url) {
      // For YouTube embed, update the iframe src with timestamp
      const iframe = document.getElementById('youtube-player-iframe');
      if (iframe) {
        const baseUrl = transcript.youtube_embed_url.split('?')[0];
        const timestamp = Math.floor(startTime);
        iframe.src = `${baseUrl}?start=${timestamp}&autoplay=1`;
      }
    } else if (videoRef.current) {
      videoRef.current.currentTime = startTime;
      videoRef.current.play();
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const isSolutionSegment = (index) => {
    return transcript?.solution_segments?.includes(index) || false;
  };

  const isCurrentSegment = (segment) => {
    // For YouTube embed, we can't track current time, so disable highlighting
    if (transcript.video_unavailable) {
      return false;
    }
    return currentTime >= segment.start && currentTime <= segment.end;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-400">Transcribing video and identifying solutions...</p>
          <p className="text-sm text-gray-500 mt-2">This may take a minute</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-white">
        <div className="container mx-auto px-4 py-8">
          <button
            onClick={() => navigate('/chat')}
            className="text-gray-400 hover:text-white mb-6"
          >
            ← Back to Chat
          </button>
          <div className="bg-red-500 bg-opacity-20 border border-red-500 rounded-xl p-8 max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold text-red-400 mb-4">Error</h2>
            <p className="text-gray-300">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!transcript) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate('/chat')}
            className="text-gray-400 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition"
          >
            ← Back to Chat
          </button>
          <div className="flex items-center gap-4">
            <span className="text-gray-400">Welcome, {user?.username}</span>
            <button
              onClick={() => navigate('/')}
              className="text-gray-400 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition"
            >
              Home
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Player - Takes 2/3 of the width */}
          <div className="lg:col-span-2">
            {transcript.video_unavailable ? (
              <div className="bg-black rounded-xl overflow-hidden mb-4">
                <div className="bg-yellow-600 bg-opacity-20 border border-yellow-500 rounded-lg p-4 mb-4">
                  <p className="text-yellow-300 text-sm">
                    ⚠️ Video download unavailable due to YouTube restrictions. Showing YouTube embed player instead.
                  </p>
                  <p className="text-yellow-400 text-xs mt-1">
                    {transcript.video_unavailable_reason}
                  </p>
                </div>
                {transcript.youtube_embed_url && (
                  <div className="bg-black rounded-lg overflow-hidden">
                    <iframe
                      id="youtube-player-iframe"
                      width="100%"
                      height="500"
                      src={transcript.youtube_embed_url}
                      title="YouTube video player"
                      frameBorder="0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                      className="w-full"
                    ></iframe>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-black rounded-xl overflow-hidden mb-4">
                <video
                  ref={videoRef}
                  controls
                  className="w-full"
                  src={transcript.video_url || `/api/video/stream/${videoId}`}
                  onLoadedMetadata={() => {
                    if (videoRef.current) {
                      videoRef.current.currentTime = 0;
                    }
                  }}
                >
                  Your browser does not support the video tag.
                </video>
              </div>
            )}

            {/* Video Info */}
            <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4 mb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Duration: {formatTime(transcript.duration)}</p>
                  <p className="text-sm text-gray-400">Language: {transcript.language}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-purple-400">
                    ⭐ {transcript.solution_segments?.length || 0} Solution Segments
                  </p>
                  <p className="text-xs text-gray-500">
                    {transcript.total_segments} Total Segments
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Transcript Sidebar - Takes 1/3 of the width */}
          <div className="lg:col-span-1">
            <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4 h-[calc(100vh-200px)] flex flex-col">
              <h2 className="text-xl font-bold text-purple-400 mb-4 flex items-center gap-2">
                📜 Transcript
                <span className="text-xs text-gray-400 font-normal">
                  ({transcript.segments?.length || 0} segments)
                </span>
              </h2>

              <div className="flex-1 overflow-y-auto space-y-2 pr-2">
                {transcript.segments?.map((segment, index) => {
                  const isSolution = isSolutionSegment(index);
                  const isCurrent = isCurrentSegment(segment);
                  
                  return (
                    <div
                      key={index}
                      onClick={() => jumpToTimestamp(segment.start)}
                      className={`
                        p-3 rounded-lg cursor-pointer transition-all duration-200
                        ${isCurrent 
                          ? 'bg-purple-600 bg-opacity-30 border-2 border-purple-500' 
                          : 'bg-[#1a1a1a] border border-[#2a2a2a] hover:bg-[#252525] hover:border-purple-600/50'
                        }
                        ${isSolution ? 'ring-2 ring-yellow-500 ring-opacity-50' : ''}
                      `}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <span className="text-xs font-mono text-purple-400 font-semibold">
                          {segment.timestamp}
                        </span>
                        {isSolution && (
                          <span className="text-xs bg-yellow-500 bg-opacity-20 text-yellow-300 px-2 py-0.5 rounded">
                            ⭐ Solution
                          </span>
                        )}
                      </div>
                      <p className={`text-sm leading-relaxed ${isSolution ? 'text-yellow-200 font-medium' : 'text-gray-300'}`}>
                        {segment.text}
                      </p>
                    </div>
                  );
                })}
              </div>

              {/* Solution Segments Summary */}
              {transcript.solution_segments && transcript.solution_segments.length > 0 && (
                <div className="mt-4 pt-4 border-t border-[#2a2a2a]">
                  <p className="text-xs text-gray-400 mb-2">
                    💡 Click on highlighted segments (⭐) to jump to solution parts
                  </p>
                  <button
                    onClick={() => {
                      const firstSolution = transcript.solution_segments[0];
                      if (firstSolution < transcript.segments.length) {
                        jumpToTimestamp(transcript.segments[firstSolution].start);
                      }
                    }}
                    className="w-full px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg text-sm font-semibold transition"
                  >
                    Jump to First Solution
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default VideoPlayerPage;

