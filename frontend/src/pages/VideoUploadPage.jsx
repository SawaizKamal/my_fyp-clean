import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/config';

function VideoUploadPage() {
  const navigate = useNavigate();
  const { user, isAuthenticated, loading: authLoading, token } = useAuth();
  // #region agent log
  if (process.env.NODE_ENV === 'development') {
    fetch('http://127.0.0.1:7243/ingest/437f7cb7-d9e7-437e-82fe-e00f0e39dcc2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'VideoUploadPage.jsx:9',message:'Component initialized',data:{hasUser:!!user,isAuthenticated,hasToken:!!token,authLoading},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
  }
  // #endregion
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [transcript, setTranscript] = useState(null);
  const [error, setError] = useState(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [userQuery, setUserQuery] = useState('');
  const [progress, setProgress] = useState(0);
  const [taskId, setTaskId] = useState(null);
  const pollIntervalRef = useRef(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login');
    }
  }, [authLoading, isAuthenticated, navigate]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Update current time from video player
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !transcript) return;

    const updateTime = () => {
      setCurrentTime(video.currentTime);
    };

    video.addEventListener('timeupdate', updateTime);
    return () => video.removeEventListener('timeupdate', updateTime);
  }, [transcript]);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // Validate file type
      if (!selectedFile.type.startsWith('video/')) {
        setError('Please select a video file');
        return;
      }
      
      // Validate file size (500MB limit)
      const MAX_SIZE = 500 * 1024 * 1024; // 500MB
      if (selectedFile.size > MAX_SIZE) {
        setError('File size must be less than 500MB');
        return;
      }
      
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a video file');
      return;
    }

    // Check if user is authenticated
    if (!isAuthenticated) {
      setError('You must be logged in to upload videos. Redirecting to login...');
      setTimeout(() => navigate('/login'), 2000);
      return;
    }

    setError(null);
    setUploading(true);
    setTranscribing(true);
    setProgress(0);
    setTranscript(null);

    let progressInterval = null;

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Add user query if provided (for solution detection)
      if (userQuery.trim()) {
        formData.append('user_query', userQuery.trim());
      }
      
      // #region agent log
      if (process.env.NODE_ENV === 'development') {
        fetch('http://127.0.0.1:7243/ingest/437f7cb7-d9e7-437e-82fe-e00f0e39dcc2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'VideoUploadPage.jsx:91',message:'Before API call',data:{hasToken:!!token,isAuthenticated,fileSelected:!!file,hasUserQuery:!!userQuery.trim()},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      }
      // #endregion
      if (process.env.NODE_ENV === 'development') {
        console.log('Uploading video with token:', token ? 'Present' : 'Missing');
      }

      // Simulate progress updates (since we can't get real-time progress from Whisper)
      progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev < 90) return prev + 5;
          return prev;
        });
      }, 500);

      // Note: Don't set Content-Type header - axios will set it automatically with boundary for FormData
      const response = await api.post('/transcribe/local', formData);

      // Check if we got a task_id (background task) or immediate results
      if (response.data.task_id) {
        // Background task - start polling
        setTaskId(response.data.task_id);
        if (progressInterval) clearInterval(progressInterval);
        
        // Poll for status
        pollIntervalRef.current = setInterval(async () => {
          try {
            const statusResponse = await api.get(`/transcribe/status/${response.data.task_id}`);
            const status = statusResponse.data;
            
            setProgress(status.progress || 0);
            
            if (status.status === 'completed') {
              if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
              setProgress(100);
              setTranscript({
                video_id: status.video_id,
                video_url: status.video_url,
                filename: status.filename,
                segments: status.segments,
                solution_segments: status.solution_segments,
                full_transcript: status.full_transcript,
                duration: status.duration,
                language: status.language,
                total_segments: status.total_segments
              });
              setUploading(false);
              setTranscribing(false);
            } else if (status.status === 'failed') {
              if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
              setError(status.error || 'Transcription failed');
              setUploading(false);
              setTranscribing(false);
            }
          } catch (pollErr) {
            console.error('Polling error:', pollErr);
            // Continue polling on error
          }
        }, 2000); // Poll every 2 seconds
        
        // Clean up polling on component unmount or error
        // Store in a ref or handle cleanup in finally block
      } else {
        // Immediate results (fallback for non-Render deployments)
        if (progressInterval) clearInterval(progressInterval);
        setProgress(100);
        setTranscript(response.data);
        setUploading(false);
        setTranscribing(false);
      }
      
    } catch (err) {
      if (progressInterval) clearInterval(progressInterval);
      console.error('Transcription error:', err);
      console.error('Error response:', err.response);
      
      // Handle different error status codes
      if (err.response?.status === 401) {
        setError('Your session has expired. Redirecting to login...');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
        return;
      }
      
      if (err.response?.status === 502 || err.response?.status === 503) {
        setError('Server is temporarily unavailable. Please try again in a few moments.');
        return;
      }
      
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to transcribe video. Please try again.';
      setError(errorMessage);
    } finally {
      setUploading(false);
      setTranscribing(false);
    }
  };

  const jumpToTimestamp = (startTime) => {
    if (videoRef.current) {
      const video = videoRef.current;
      
      // Wait for video to be ready for seeking
      if (video.readyState < 2) {
        // Video metadata not loaded yet, wait for it
        const seekWhenReady = () => {
          video.currentTime = startTime;
          video.play().catch(err => {
            console.error('Error playing video:', err);
          });
        };
        video.addEventListener('loadedmetadata', seekWhenReady, { once: true });
        // Also try to load if not already loading
        if (video.readyState === 0) {
          video.load();
        }
      } else {
        // Video is ready, seek immediately
        video.currentTime = startTime;
        video.play().catch(err => {
          console.error('Error playing video:', err);
        });
      }
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
    return currentTime >= segment.start && currentTime <= segment.end;
  };

  // Show loading while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 grid-overlay opacity-20"></div>
        <div className="text-center relative z-10">
          <div className="relative">
            <div className="animate-spin rounded-full h-20 w-20 border-4 border-[#00ff41] border-t-transparent mx-auto mb-4 animate-neon-pulse"></div>
            <div className="absolute inset-0 rounded-full border-4 border-[#ff00ff] border-t-transparent animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
          </div>
          <p className="text-[#00ff41] font-mono text-lg animate-neon-glow">> INITIALIZING SYSTEM...</p>
        </div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 grid-overlay opacity-20"></div>
      <div className="absolute top-0 left-0 w-96 h-96 bg-[#ff0040] opacity-5 blur-3xl animate-float"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-[#00ff41] opacity-5 blur-3xl animate-float" style={{ animationDelay: '1s' }}></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 animate-slide-in-left">
          <button
            onClick={() => navigate('/chat')}
            className="glass text-[#00ff41] hover:text-black hover:bg-[#00ff41] px-6 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm border border-[#00ff41]"
          >
            < BACK TO CHAT
          </button>
          <div className="flex items-center gap-4">
            <span className="text-gray-300 font-mono text-sm">[ {user?.username} ]</span>
            <button
              onClick={() => navigate('/')}
              className="glass text-[#ff00ff] hover:text-black hover:bg-[#ff00ff] px-6 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm border border-[#ff00ff]"
            >
              > HOME
            </button>
          </div>
        </div>

        {/* Main Content */}
        {!transcript ? (
          <div className="max-w-4xl mx-auto animate-fade-in">
            <div className="glass-neon rounded-xl p-8 mb-6 border-2">
              <h1 className="text-4xl font-black mb-6 neon-text-green font-mono uppercase tracking-wider animate-neon-glow">
                > UPLOAD VIDEO FOR TRANSCRIPTION
              </h1>
              
              {/* File Upload */}
              <div className="mb-6">
                <label className="block text-sm font-bold text-[#00ff41] mb-3 font-mono uppercase">
                  > SELECT VIDEO FILE
                </label>
                <div className="flex items-center gap-4">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="px-8 py-4 bg-gradient-to-r from-[#ff0040] to-[#ff00ff] hover:from-[#ff00ff] hover:to-[#00ff41] rounded-lg font-black transition-all duration-300 cyber-button font-mono text-sm uppercase tracking-wider transform hover:scale-105 animate-neon-pulse"
                    style={{ boxShadow: '0 0 20px rgba(255, 0, 64, 0.5)' }}
                  >
                    > CHOOSE FILE
                  </button>
                  {file && (
                    <div className="glass border border-[#00ff41] rounded-lg px-4 py-2">
                      <span className="text-[#00ff41] font-mono text-sm">
                        {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* User Query (Optional) */}
              <div className="mb-6">
                <label className="block text-sm font-bold text-[#ff00ff] mb-2 font-mono uppercase">
                  > PROBLEM QUERY (OPTIONAL)
                </label>
                <p className="text-xs text-gray-400 mb-3 font-mono">
                  Provide a question or problem description to help identify solution segments
                </p>
                <textarea
                  value={userQuery}
                  onChange={(e) => setUserQuery(e.target.value)}
                  placeholder="e.g., How do I fix this error? How does this algorithm work?"
                  className="w-full px-4 py-3 rounded-xl bg-black/80 text-[#00ff41] placeholder-gray-500 border-2 border-[#ff00ff] focus:outline-none focus:ring-2 focus:ring-[#ff00ff] focus:border-[#ff00ff] min-h-[100px] transition-all duration-300 font-mono text-sm focus:shadow-[0_0_20px_rgba(255,0,255,0.3)]"
                  rows="3"
                />
              </div>

              {/* Error Display */}
              {error && (
                <div className="glass border-2 border-[#ff0040] text-[#ff0040] px-6 py-4 rounded-xl mb-6 animate-slide-in-left" style={{ boxShadow: '0 0 20px rgba(255, 0, 64, 0.5)' }}>
                  <div className="flex items-center gap-2 font-mono font-bold">
                    <span>> ERROR:</span>
                    <span className="font-normal">{error}</span>
                  </div>
                </div>
              )}

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={!file || uploading}
                className="w-full px-8 py-5 bg-gradient-to-r from-[#ff0040] via-[#ff00ff] to-[#00ff41] hover:from-[#ff00ff] hover:via-[#00ff41] hover:to-[#ff0040] rounded-xl font-black transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed cyber-button font-mono text-lg uppercase tracking-wider transform hover:scale-105 disabled:transform-none"
                style={{ boxShadow: '0 0 30px rgba(255, 0, 64, 0.5), 0 0 60px rgba(255, 0, 255, 0.3)' }}
              >
                {uploading ? '> PROCESSING...' : '> UPLOAD & TRANSCRIBE'}
              </button>

              {/* Progress Bar */}
              {(uploading || transcribing) && (
                <div className="mt-6 animate-fade-in">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-mono text-[#00ff41] uppercase">
                      > {transcribing ? 'TRANSCRIBING VIDEO...' : 'UPLOADING...'}
                    </span>
                    <span className="text-sm font-mono font-bold text-[#ff00ff] neon-text-pink">{progress}%</span>
                  </div>
                  <div className="w-full bg-black/80 rounded-full h-3 border-2 border-[#00ff41] overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-[#ff0040] via-[#ff00ff] to-[#00ff41] h-full rounded-full transition-all duration-300 relative"
                      style={{ width: `${progress}%`, boxShadow: '0 0 20px rgba(255, 0, 255, 0.8)' }}
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-scan-line"></div>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mt-3 font-mono">
                    > Processing time varies based on video length...
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Video Player with Transcript */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
            {/* Video Player - Takes 2/3 of the width */}
            <div className="lg:col-span-2">
              <div className="bg-black rounded-xl overflow-hidden mb-4 border-2 border-[#00ff41] shadow-[0_0_30px_rgba(0,255,65,0.3)]">
                <video
                  ref={videoRef}
                  controls
                  preload="metadata"
                  className="w-full"
                  src={transcript.video_id ? `${api.defaults.baseURL}/video/${transcript.video_id}?token=${token}` : undefined}
                  onLoadedMetadata={() => {
                    if (videoRef.current) {
                      videoRef.current.currentTime = 0;
                    }
                  }}
                  onError={(e) => {
                    console.error('Video error:', e);
                    const video = e.target;
                    if (video.error) {
                      console.error('Video error details:', {
                        error: video.error,
                        errorCode: video.error?.code,
                        errorMessage: video.error?.message,
                        networkState: video.networkState,
                        readyState: video.readyState,
                        src: video.src
                      });
                    }
                  }}
                >
                  Your browser does not support the video tag.
                </video>
              </div>

              {/* Video Info */}
              <div className="glass-neon rounded-xl p-4 mb-4 border-2">
                <div className="flex items-center justify-between">
                  <div className="font-mono text-sm space-y-1">
                    <p className="text-[#00ff41]">> FILE: <span className="text-white">{transcript.filename}</span></p>
                    <p className="text-[#00ff41]">> DURATION: <span className="text-white">{formatTime(transcript.duration)}</span></p>
                    <p className="text-[#00ff41]">> LANGUAGE: <span className="text-white">{transcript.language}</span></p>
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

              {/* Reset Button */}
              <button
                onClick={() => {
                  setTranscript(null);
                  setFile(null);
                  setProgress(0);
                  setError(null);
                  if (fileInputRef.current) {
                    fileInputRef.current.value = '';
                  }
                }}
                className="px-6 py-3 glass border border-[#ff0040] text-[#ff0040] hover:bg-[#ff0040] hover:text-black rounded-lg font-bold transition-all duration-300 cyber-button font-mono text-sm uppercase mb-4"
              >
                > UPLOAD ANOTHER VIDEO
              </button>
            </div>

            {/* Transcript Sidebar - Takes 1/3 of the width */}
            <div className="lg:col-span-1">
              <div className="glass-neon rounded-xl p-4 h-[calc(100vh-200px)] flex flex-col border-2">
                <h2 className="text-xl font-black neon-text-green mb-4 flex items-center gap-2 font-mono uppercase tracking-wider">
                  > TRANSCRIPT
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
                        onClick={() => jumpToTimestamp(segment.start)}
                        className={`
                          p-3 rounded-lg cursor-pointer transition-all duration-300 font-mono text-sm
                          ${isCurrent 
                            ? 'glass-neon border-2 border-[#00ff41] shadow-[0_0_20px_rgba(0,255,65,0.5)]' 
                            : 'glass border border-[#ff00ff] hover:border-[#00ff41] hover:shadow-[0_0_10px_rgba(0,255,65,0.3)]'
                          }
                          ${isSolution ? 'ring-2 ring-[#ff00ff] ring-opacity-70 bg-[#ff00ff] bg-opacity-10' : ''}
                          ${isSolution && isCurrent ? 'ring-4 ring-[#ff00ff] ring-opacity-90 shadow-[0_0_30px_rgba(255,0,255,0.6)]' : ''}
                        `}
                        style={{
                          transform: isCurrent ? 'scale(1.02)' : 'scale(1)',
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
                            > {segment.timestamp}
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
                      > Click highlighted segments (⭐) to jump to solutions
                    </p>
                    <div className="space-y-2">
                      <button
                        onClick={() => {
                          const firstSolution = transcript.solution_segments[0];
                          if (firstSolution < transcript.segments.length) {
                            jumpToTimestamp(transcript.segments[firstSolution].start);
                          }
                        }}
                        className="w-full px-4 py-2 glass border border-[#ff00ff] text-[#ff00ff] hover:bg-[#ff00ff] hover:text-black rounded-lg text-sm font-bold transition-all duration-300 transform hover:scale-105 cyber-button font-mono uppercase"
                      >
                        ⭐ JUMP TO FIRST SOLUTION
                      </button>
                      {transcript.solution_segments.length > 1 && (
                        <button
                          onClick={() => {
                            const firstSolutionIndex = transcript.solution_segments[0];
                            const element = document.querySelector(`[data-segment-index="${firstSolutionIndex}"]`);
                            if (element) {
                              element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            }
                          }}
                          className="w-full px-4 py-2 glass border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black rounded-lg text-sm font-bold transition-all duration-300 transform hover:scale-105 cyber-button font-mono uppercase"
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
        )}
      </div>
    </div>
  );
}

export default VideoUploadPage;

