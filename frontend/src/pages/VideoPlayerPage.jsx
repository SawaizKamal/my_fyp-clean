import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/config';

function VideoPlayerPage() {
  const { videoId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const videoRef = useRef(null);
  const youtubePlayerRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [highlightedSegment, setHighlightedSegment] = useState(null);
  const [youtubeApiReady, setYoutubeApiReady] = useState(false);
  const [videoInitialized, setVideoInitialized] = useState(false);
  const [videoSrc, setVideoSrc] = useState('');
  const isSeekingRef = useRef(false);

  // Initialize YouTube IFrame API
  useEffect(() => {
    // Check if YouTube IFrame API is already loaded
    if (window.YT && window.YT.Player) {
      setYoutubeApiReady(true);
      return;
    }

    // Wait for YouTube IFrame API to load
    const checkYoutubeAPI = setInterval(() => {
      if (window.YT && window.YT.Player) {
        setYoutubeApiReady(true);
        clearInterval(checkYoutubeAPI);
      }
    }, 100);

    // Set up global callback for YouTube API
    window.onYouTubeIframeAPIReady = () => {
      setYoutubeApiReady(true);
      clearInterval(checkYoutubeAPI);
    };

    return () => {
      clearInterval(checkYoutubeAPI);
      delete window.onYouTubeIframeAPIReady;
    };
  }, []);

  // Initialize YouTube player when API is ready and transcript is loaded
  useEffect(() => {
    if (!youtubeApiReady || !transcript || !transcript.video_unavailable || !transcript.youtube_embed_url) {
      return;
    }

    const videoIdFromUrl = transcript.youtube_embed_url.match(/embed\/([^?]+)/)?.[1] || videoId;
    
    if (videoIdFromUrl && window.YT && window.YT.Player) {
      // Destroy existing player if any
      if (youtubePlayerRef.current) {
        try {
          youtubePlayerRef.current.destroy();
        } catch (e) {
          console.log('Error destroying previous player:', e);
        }
      }

      // Create new YouTube player
      youtubePlayerRef.current = new window.YT.Player('youtube-player-iframe', {
        videoId: videoIdFromUrl,
        playerVars: {
          autoplay: 0,
          controls: 1,
          enablejsapi: 1,
          origin: window.location.origin,
        },
        events: {
          onReady: (event) => {
            console.log('YouTube player ready');
          },
          onStateChange: (event) => {
            // Track video state changes if needed
          },
          onError: (event) => {
            console.error('YouTube player error:', event.data);
          }
        }
      });
    }

    return () => {
      if (youtubePlayerRef.current) {
        try {
          youtubePlayerRef.current.destroy();
        } catch (e) {
          console.log('Error destroying player on cleanup:', e);
        }
        youtubePlayerRef.current = null;
      }
    };
  }, [youtubeApiReady, transcript, videoId]);

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
        if (process.env.NODE_ENV === 'development') {
          fetch('http://127.0.0.1:7242/ingest/7b7349a8-4aec-40c0-88c1-85a8567508ca',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'VideoPlayerPage.jsx:25',message:'Before API call',data:{videoId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'FRONTEND'})}).catch(()=>{});
        }
        // #endregion

        // Call transcription API
        const response = await api.post(`/video/transcribe/${videoId}`);
        
        // #region agent log
        if (process.env.NODE_ENV === 'development') {
          fetch('http://127.0.0.1:7242/ingest/7b7349a8-4aec-40c0-88c1-85a8567508ca',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'VideoPlayerPage.jsx:30',message:'API call succeeded',data:{hasData:!!response.data},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'FRONTEND'})}).catch(()=>{});
        }
        // #endregion
        
        setTranscript(response.data);
        setVideoInitialized(false); // Reset when new transcript loads
        
        // Set stable video src when transcript loads
        const transcriptData = response.data;
        if (transcriptData && transcriptData.video_id) {
          const token = localStorage.getItem('token');
          // Construct video URL using video_id (not video_url from backend)
          // Use GET /api/video/{video_id} endpoint for playback
          const finalVideoUrl = `${api.defaults.baseURL}/video/${transcriptData.video_id}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
          console.log('=== Video URL Debug ===');
          console.log('Video ID:', transcriptData.video_id);
          console.log('Final video src:', finalVideoUrl);
          console.log('======================');
          setVideoSrc(finalVideoUrl);
        } else {
          setVideoSrc('');
        }
      } catch (err) {
        // #region agent log
        if (process.env.NODE_ENV === 'development') {
          fetch('http://127.0.0.1:7242/ingest/7b7349a8-4aec-40c0-88c1-85a8567508ca',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'VideoPlayerPage.jsx:33',message:'API call failed',data:{error:err.message,status:err.response?.status,detail:err.response?.data?.detail},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'FRONTEND'})}).catch(()=>{});
        }
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
    console.log('Jumping to timestamp:', startTime);
    
    if (transcript?.video_unavailable && transcript.youtube_embed_url) {
      // Use YouTube IFrame API if available for better control
      if (youtubePlayerRef.current && youtubeApiReady) {
        try {
          // Seek without autoplay - let user control playback
          youtubePlayerRef.current.seekTo(startTime, true);
          // Don't auto-play - just seek
        } catch (e) {
          console.error('Error seeking with YouTube API:', e);
          // Fallback to iframe src method
          const iframe = document.getElementById('youtube-player-iframe');
          if (iframe) {
            const baseUrl = transcript.youtube_embed_url.split('?')[0];
            const timestamp = Math.floor(startTime);
            // Remove autoplay from fallback too
            iframe.src = `${baseUrl}?start=${timestamp}&enablejsapi=1`;
          }
        }
      } else {
        // Fallback: update iframe src with timestamp
        const iframe = document.getElementById('youtube-player-iframe');
        if (iframe) {
          const baseUrl = transcript.youtube_embed_url.split('?')[0];
          const timestamp = Math.floor(startTime);
          // Remove autoplay
          const newUrl = `${baseUrl}?start=${timestamp}&enablejsapi=1`;
          iframe.src = newUrl;
        }
      }
    } else if (videoRef.current) {
      // For regular video element, seek using standard HTML5 API
      const video = videoRef.current;
      
      // Check if video is ready to seek
      if (video.readyState < 2) {
        // Video metadata not loaded yet, wait for it
        const seekWhenReady = () => {
          video.currentTime = startTime;
          setCurrentTime(startTime);
        };
        video.addEventListener('loadedmetadata', seekWhenReady, { once: true });
        return;
      }
      
      // Set seeking flag to prevent interference
      isSeekingRef.current = true;
      
      // Direct seek - this is the standard HTML5 video API
      // Setting currentTime directly does NOT reload the video
      try {
        video.currentTime = startTime;
        
        // Update state immediately for UI feedback
        setCurrentTime(startTime);
        
        // Clear seeking flag after seek completes
        const handleSeeked = () => {
          isSeekingRef.current = false;
          setCurrentTime(video.currentTime);
        };
        video.addEventListener('seeked', handleSeeked, { once: true });
      } catch (e) {
        console.error('Error seeking video:', e);
        isSeekingRef.current = false;
      }
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const isSolutionSegment = (index) => {
    if (!transcript?.solution_segments) return false;
    // Handle both array of numbers and array of objects
    if (Array.isArray(transcript.solution_segments)) {
      // Check if it's an array of numbers (indices)
      if (transcript.solution_segments.length > 0 && typeof transcript.solution_segments[0] === 'number') {
        return transcript.solution_segments.includes(index);
      }
      // Check if it's an array of objects with index property
      if (transcript.solution_segments.length > 0 && typeof transcript.solution_segments[0] === 'object') {
        return transcript.solution_segments.some(seg => seg.index === index || seg === index);
      }
    }
    return false;
  };

  const isCurrentSegment = (segment) => {
    // For YouTube embed, try to get current time from player if API is available
    if (transcript.video_unavailable) {
      if (youtubePlayerRef.current && youtubeApiReady) {
        try {
          const ytCurrentTime = youtubePlayerRef.current.getCurrentTime();
          return ytCurrentTime >= segment.start && ytCurrentTime <= segment.end;
        } catch (e) {
          return false;
        }
      }
      return false;
    }
    return currentTime >= segment.start && currentTime <= segment.end;
  };

  // Update current time from YouTube player if available
  useEffect(() => {
    if (!transcript?.video_unavailable || !youtubePlayerRef.current || !youtubeApiReady) {
      return;
    }

    const updateYouTubeTime = setInterval(() => {
      try {
        if (youtubePlayerRef.current) {
          const ytTime = youtubePlayerRef.current.getCurrentTime();
          setCurrentTime(ytTime);
        }
      } catch (e) {
        // Player might not be ready yet
      }
    }, 500); // Update every 500ms

    return () => clearInterval(updateYouTubeTime);
  }, [transcript?.video_unavailable, youtubeApiReady]);

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 grid-overlay opacity-20"></div>
        <div className="text-center relative z-10">
          <div className="relative">
            <div className="animate-spin rounded-full h-20 w-20 border-4 border-[#00ff41] border-t-transparent mx-auto mb-4 animate-neon-pulse"></div>
            <div className="absolute inset-0 rounded-full border-4 border-[#ff00ff] border-t-transparent animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
          </div>
          <p className="text-[#00ff41] font-mono text-lg animate-neon-glow">{'>'} TRANSCRIBING VIDEO AND IDENTIFYING SOLUTIONS...</p>
          <p className="text-sm text-gray-400 mt-2 font-mono">This may take a minute</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-black text-white relative overflow-hidden">
        <div className="absolute inset-0 grid-overlay opacity-20"></div>
        <div className="container mx-auto px-4 py-8 relative z-10">
          <button
            onClick={() => navigate('/chat')}
            className="glass border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black mb-6 flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm uppercase"
          >
            {'<'} BACK TO CHAT
          </button>
          <div className="glass border-2 border-[#ff0040] rounded-xl p-8 max-w-2xl mx-auto animate-fade-in" style={{ boxShadow: '0 0 30px rgba(255, 0, 64, 0.5)' }}>
            <h2 className="text-3xl font-black neon-text-red mb-4 flex items-center gap-2 font-mono uppercase tracking-wider">
              <span>⚠️</span> ERROR LOADING TRANSCRIPTION
            </h2>
            <p className="text-gray-300 mb-4 font-mono">{'>'} {error}</p>
            <div className="glass border border-[#ff00ff] rounded-lg p-4 mb-4">
              <p className="text-[#ff00ff] text-sm font-mono font-bold">
                {'>'} POSSIBLE SOLUTIONS:
              </p>
              <ul className="list-disc list-inside text-gray-300 text-sm mt-2 space-y-1 font-mono">
                <li>Try again in a few moments (YouTube may be temporarily blocking requests)</li>
                <li>Check if the video has captions/transcripts enabled</li>
                <li>Try a different video</li>
                <li>Watch the video directly on YouTube if transcription is unavailable</li>
              </ul>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-3 glass border-2 border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black rounded-lg font-black transition-all duration-300 cyber-button font-mono uppercase tracking-wider"
              >
              {'>'} RETRY
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!transcript) {
    return null;
  }

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 grid-overlay opacity-20"></div>
      <div className="absolute top-0 right-0 w-96 h-96 bg-[#ff00ff] opacity-5 blur-3xl animate-float"></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 animate-slide-in-left">
          <button
            onClick={() => navigate('/chat')}
            className="glass border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black px-4 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm uppercase"
          >
            {'<'} BACK TO CHAT
          </button>
          <div className="flex items-center gap-4">
            <span className="text-gray-300 font-mono text-sm">[ {user?.username} ]</span>
            <button
              onClick={() => navigate('/')}
              className="glass border border-[#ff00ff] text-[#ff00ff] hover:bg-[#ff00ff] hover:text-black px-4 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm uppercase"
            >
              {'>'} HOME
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
                      allow="autoplay"
                    ></iframe>
                    <p className="text-xs text-gray-500 mt-2 text-center">
                      💡 Click on transcript timestamps to jump to specific moments in the video
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-black rounded-xl overflow-hidden mb-4">
                <video
                  ref={videoRef}
                  controls
                  className="w-full"
                  preload="metadata"
                  src={videoSrc}
                  onLoadedMetadata={(e) => {
                    // Only initialize once when video first loads
                    // Don't reset if we're currently seeking
                    if (videoRef.current && !videoInitialized && !isSeekingRef.current) {
                      // Set to 0 only on very first load
                      if (videoRef.current.currentTime === 0 || videoRef.current.readyState < 2) {
                        videoRef.current.currentTime = 0;
                      }
                      setVideoInitialized(true);
                      // Ensure video doesn't autoplay
                      if (!videoRef.current.paused) {
                        videoRef.current.pause();
                      }
                    }
                  }}
                  onSeeking={(e) => {
                    // Prevent any interference during seek
                    console.log('Video seeking to:', e.target.currentTime);
                    // Make sure we don't reset to 0 during seek
                    if (e.target.currentTime === 0 && isSeekingRef.current) {
                      // If we're seeking and it resets to 0, something went wrong
                      console.warn('Video reset to 0 during seek - this should not happen');
                    }
                  }}
                  onSeeked={(e) => {
                    // Update current time after seek completes
                    const newTime = e.target.currentTime;
                    setCurrentTime(newTime);
                    console.log('Video seeked to:', newTime);
                    // Clear seeking flag after seek completes
                    isSeekingRef.current = false;
                  }}
                  onPlay={() => {
                    // Optional: Track when video plays for debugging
                    console.log('Video started playing');
                  }}
                  onPause={() => {
                    // Optional: Track when video pauses for debugging
                    console.log('Video paused');
                  }}
                  onError={(e) => {
                    console.error('Video error:', e);
                    const video = e.target;
                    console.error('Video error details:', {
                      error: video.error,
                      errorCode: video.error?.code,
                      errorMessage: video.error?.message,
                      networkState: video.networkState,
                      readyState: video.readyState,
                      src: video.src,
                      currentSrc: video.currentSrc
                    });
                    if (video.error) {
                      setError(`Video playback error: ${video.error.message || 'Unknown error'}`);
                    }
                  }}
                  onLoadStart={() => {
                    console.log('Video load started, src:', videoSrc);
                  }}
                  onCanPlay={() => {
                    console.log('Video can play');
                  }}
                >
                  Your browser does not support the video tag.
                </video>
              </div>
            )}

            {/* Video Info */}
            <div className="glass-neon rounded-xl p-4 mb-4 border-2">
              <div className="flex items-center justify-between">
                <div className="font-mono text-sm space-y-1">
                  <p className="text-[#00ff41]">{'>'} DURATION: <span className="text-white">{formatTime(transcript.duration)}</span></p>
                  <p className="text-[#00ff41]">{'>'} LANGUAGE: <span className="text-white">{transcript.language}</span></p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-mono font-bold neon-text-pink">
                    ⭐ {transcript.solution_segments?.length || 0} SOLUTION SEGMENTS
                  </p>
                  <p className="text-xs text-gray-400 font-mono">
                    {transcript.total_segments} TOTAL SEGMENTS
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Transcript Sidebar - Takes 1/3 of the width */}
          <div className="lg:col-span-1">
            <div className="glass-neon rounded-xl p-4 h-[calc(100vh-200px)] flex flex-col border-2">
              <h2 className="text-xl font-black neon-text-green mb-4 flex items-center gap-2 font-mono uppercase tracking-wider">
                {'>'} TRANSCRIPT
                <span className="text-xs text-gray-400 font-normal normal-case">
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
                      data-segment-index={index}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        if (segment && segment.start !== undefined) {
                          jumpToTimestamp(segment.start);
                        }
                      }}
                      onMouseDown={(e) => {
                        // Prevent text selection on click
                        if (e.detail > 1) {
                          e.preventDefault();
                        }
                      }}
                      className={`
                        p-3 rounded-lg cursor-pointer transition-all duration-300 select-none font-mono text-sm
                        ${isCurrent 
                          ? 'glass-neon border-2 border-[#00ff41] shadow-[0_0_20px_rgba(0,255,65,0.5)]' 
                          : 'glass border border-[#ff00ff] hover:border-[#00ff41] hover:shadow-[0_0_10px_rgba(0,255,65,0.3)]'
                        }
                        ${isSolution ? 'ring-2 ring-[#ff00ff] ring-opacity-70 bg-[#ff00ff] bg-opacity-10' : ''}
                        ${isSolution && isCurrent ? 'ring-4 ring-[#ff00ff] ring-opacity-90 shadow-[0_0_30px_rgba(255,0,255,0.6)]' : ''}
                      `}
                      style={{
                        transform: isCurrent ? 'scale(1.02)' : 'scale(1)',
                        userSelect: 'none',
                        WebkitUserSelect: 'none',
                      }}
                    >
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            jumpToTimestamp(segment.start);
                          }}
                          className="text-xs font-mono text-[#00ff41] font-bold hover:text-[#00ff41] hover:underline transition-colors neon-text-green"
                          >
                          {'>'} {segment.timestamp}
                        </button>
                        {isSolution && (
                          <span className="text-xs glass border border-[#ff00ff] text-[#ff00ff] px-2 py-0.5 rounded font-bold animate-neon-pulse font-mono">
                            ⭐ SOLUTION
                          </span>
                        )}
                      </div>
                      <p 
                        className={`text-sm leading-relaxed ${isSolution ? 'text-[#ff00ff] font-bold neon-text-pink' : 'text-gray-300'}`}
                        style={{
                          fontWeight: isSolution ? 700 : 400,
                        }}
                      >
                        {segment.text}
                      </p>
                    </div>
                  );
                })}
              </div>

              {/* Solution Segments Summary */}
              {transcript.solution_segments && transcript.solution_segments.length > 0 && (
                <div className="mt-4 pt-4 border-t border-[#ff00ff]">
                  <p className="text-xs text-gray-400 mb-3 font-mono">
                    {'>'} Click highlighted segments (⭐) to jump to solutions
                  </p>
                  <div className="space-y-2">
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const firstSolutionIndex = transcript.solution_segments[0];
                        if (transcript.segments && firstSolutionIndex !== undefined && firstSolutionIndex < transcript.segments.length) {
                          const segment = transcript.segments[firstSolutionIndex];
                          if (segment && segment.start !== undefined) {
                            jumpToTimestamp(segment.start);
                            // Also scroll to the segment in the transcript list
                            setTimeout(() => {
                              const element = document.querySelector(`[data-segment-index="${firstSolutionIndex}"]`);
                              if (element) {
                                element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                              }
                            }, 100);
                          }
                        }
                      }}
                      className="w-full px-4 py-2 glass border border-[#ff00ff] text-[#ff00ff] hover:bg-[#ff00ff] hover:text-black rounded-lg text-sm font-bold transition-all duration-300 transform hover:scale-105 active:scale-95 cyber-button font-mono uppercase"
                    >
                      ⭐ JUMP TO FIRST SOLUTION
                    </button>
                    {transcript.solution_segments.length > 1 && (
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          // Scroll to first solution segment in the list
                          const firstSolutionIndex = transcript.solution_segments[0];
                          const element = document.querySelector(`[data-segment-index="${firstSolutionIndex}"]`);
                          if (element) {
                            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            // Highlight it briefly
                            element.style.transition = 'all 0.3s';
                            element.style.transform = 'scale(1.05)';
                            setTimeout(() => {
                              element.style.transform = '';
                            }, 500);
                          }
                        }}
                        className="w-full px-4 py-2 glass border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black rounded-lg text-sm font-bold transition-all duration-300 transform hover:scale-105 active:scale-95 cyber-button font-mono uppercase"
                      >
                        📍 SCROLL TO SOLUTIONS
                      </button>
                    )}
                  </div>
                  <p className="text-xs neon-text-pink mt-3 text-center font-mono font-bold">
                    {transcript.solution_segments.length} SOLUTION SEGMENT{transcript.solution_segments.length !== 1 ? 'S' : ''} FOUND
                  </p>
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

