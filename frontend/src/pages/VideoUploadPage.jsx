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
        setError('File size must be less than 500MB. 💡 Suggestion: Compress the video or use a shorter clip.');
        return;
      }
      
      // Note: Duration validation (max 5 minutes) will be done on the server
      
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
        
        // Poll for status with live updates
        pollIntervalRef.current = setInterval(async () => {
          try {
            const statusResponse = await api.get(`/transcribe/status/${response.data.task_id}`);
            const status = statusResponse.data;
            
            setProgress(status.progress || 0);
            
            // Update transcript progressively if segments are available
            if (status.segments && status.segments.length > 0) {
              setTranscript({
                video_id: status.video_id,
                video_url: status.video_url,
                filename: status.filename,
                segments: status.segments,
                solution_segments: status.solution_segments || [],
                problem_segments: status.problem_segments || [],
                solution_timestamps: status.solution_timestamps || [],
                problem_timestamps: status.problem_timestamps || [],
                full_transcript: status.full_transcript || '',
                duration: status.duration || 0,
                language: status.language || 'unknown',
                total_segments: status.total_segments || status.segments.length,
                chunks_processed: status.chunks_processed,
                total_chunks: status.total_chunks
              });
            }
            
            if (status.status === 'completed') {
              if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
              setProgress(100);
              setTranscript({
                video_id: status.video_id,
                video_url: status.video_url,
                filename: status.filename,
                segments: status.segments,
                solution_segments: status.solution_segments || [],
                problem_segments: status.problem_segments || [],
                solution_timestamps: status.solution_timestamps || [],
                problem_timestamps: status.problem_timestamps || [],
                full_transcript: status.full_transcript,
                duration: status.duration,
                language: status.language,
                total_segments: status.total_segments
              });
              setUploading(false);
              setTranscribing(false);
            } else if (status.status === 'failed') {
              if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
              const errorMsg = status.error || 'Transcription failed';
              const suggestion = status.error_suggestion || 'Please try again.';
              setError(`${errorMsg}\n\n💡 Suggestion: ${suggestion}`);
              setUploading(false);
              setTranscribing(false);
            }
          } catch (pollErr) {
            console.error('Polling error:', pollErr);
            // Continue polling on error
          }
        }, 1500); // Poll every 1.5 seconds for more responsive updates
        
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

  const isProblemSegment = (index) => {
    return transcript?.problem_segments?.includes(index) || false;
  };

  const isCurrentSegment = (segment) => {
    return currentTime >= segment.start && currentTime <= segment.end;
  };

  // Show loading while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated) {
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
        {!transcript ? (
          <div className="max-w-4xl mx-auto">
            <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-8 mb-6">
              <h1 className="text-3xl font-bold text-purple-400 mb-6">Upload Video for Transcription</h1>
              
              {/* File Upload */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Select Video File
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
                    className="px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold transition"
                  >
                    Choose Video File
                  </button>
                  {file && (
                    <span className="text-gray-300">
                      {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                    </span>
                  )}
                </div>
              </div>

              {/* User Query (Optional) */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  What problem are you trying to solve? (Optional)
                </label>
                <p className="text-xs text-gray-500 mb-2">
                  Provide a question or problem description to help identify solution segments in the video
                </p>
                <textarea
                  value={userQuery}
                  onChange={(e) => setUserQuery(e.target.value)}
                  placeholder="e.g., How do I fix this error? How does this algorithm work?"
                  className="w-full px-4 py-3 rounded-xl bg-[#1a1a1a] text-white placeholder-gray-400 border border-[#2a2a2a] focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-purple-600 min-h-[100px] transition"
                  rows="3"
                />
              </div>

              {/* Error Display */}
              {error && (
                <div className="bg-red-500 bg-opacity-20 border border-red-500 text-red-300 px-6 py-4 rounded-xl mb-6">
                  {error}
                </div>
              )}

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={!file || uploading}
                className="w-full px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 rounded-xl font-semibold transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? 'Uploading & Transcribing...' : 'Upload & Transcribe Video'}
              </button>

              {/* Progress Bar */}
              {(uploading || transcribing) && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-400">
                      {transcribing ? 'Transcribing video...' : 'Uploading...'}
                    </span>
                    <span className="text-sm text-purple-400">{progress}%</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-purple-600 to-pink-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Processing video in 30-second chunks for optimal performance...
                    {transcript?.chunks_processed && transcript?.total_chunks && (
                      <span className="text-purple-400 ml-2">
                        Chunk {transcript.chunks_processed}/{transcript.total_chunks}
                      </span>
                    )}
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Video Player with Transcript */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Video Player - Takes 2/3 of the width */}
            <div className="lg:col-span-2">
              <div className="bg-black rounded-xl overflow-hidden mb-4">
                <video
                  ref={videoRef}
                  controls
                  className="w-full"
                  src={transcript.video_url ? api.defaults.baseURL + transcript.video_url : undefined}
                  onLoadedMetadata={() => {
                    if (videoRef.current) {
                      videoRef.current.currentTime = 0;
                    }
                  }}
                >
                  Your browser does not support the video tag.
                </video>
              </div>

              {/* Video Info */}
              <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-4 mb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-400">File: {transcript.filename}</p>
                    <p className="text-sm text-gray-400">Duration: {formatTime(transcript.duration)}</p>
                    <p className="text-sm text-gray-400">Language: {transcript.language}</p>
                  </div>
                  <div className="text-right">
                    <div className="flex gap-3 items-center">
                      {transcript.problem_segments?.length > 0 && (
                        <p className="text-sm text-red-400">
                          ❓ {transcript.problem_segments.length} Problem
                        </p>
                      )}
                      {transcript.solution_segments?.length > 0 && (
                        <p className="text-sm text-yellow-400">
                          ⭐ {transcript.solution_segments.length} Solution
                        </p>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      {transcript.total_segments} Total Segments
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
                className="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-semibold transition mb-4"
              >
                Upload Another Video
              </button>
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
                    const isProblem = isProblemSegment(index);
                    const isCurrent = isCurrentSegment(segment);
                    
                    return (
                      <div
                        key={index}
                        data-segment-index={index}
                        onClick={() => jumpToTimestamp(segment.start)}
                        className={`
                          p-3 rounded-lg cursor-pointer transition-all duration-200
                          ${isCurrent 
                            ? 'bg-purple-600 bg-opacity-30 border-2 border-purple-500 shadow-lg shadow-purple-500/50' 
                            : 'bg-[#1a1a1a] border border-[#2a2a2a] hover:bg-[#252525] hover:border-purple-600/50'
                          }
                          ${isSolution ? 'ring-2 ring-yellow-500 ring-opacity-70 bg-yellow-500 bg-opacity-10' : ''}
                          ${isProblem ? 'ring-2 ring-red-500 ring-opacity-50 bg-red-500 bg-opacity-5' : ''}
                          ${isSolution && isCurrent ? 'ring-4 ring-yellow-400 ring-opacity-80' : ''}
                          ${isProblem && isCurrent ? 'ring-4 ring-red-400 ring-opacity-60' : ''}
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
                            className="text-xs font-mono text-purple-400 font-semibold hover:text-purple-300 hover:underline transition-colors"
                          >
                            {segment.timestamp}
                          </button>
                          <div className="flex gap-1">
                            {isProblem && (
                              <span className="text-xs bg-red-500 bg-opacity-30 text-red-200 px-2 py-0.5 rounded font-semibold">
                                ❓ Problem
                              </span>
                            )}
                            {isSolution && (
                              <span className="text-xs bg-yellow-500 bg-opacity-30 text-yellow-200 px-2 py-0.5 rounded font-semibold animate-pulse">
                                ⭐ Solution
                              </span>
                            )}
                          </div>
                        </div>
                        <p 
                          className={`text-sm leading-relaxed ${
                            isSolution ? 'text-yellow-100 font-semibold' : 
                            isProblem ? 'text-red-200 font-medium' : 
                            'text-gray-300'
                          }`}
                          style={{
                            fontWeight: isSolution ? 600 : isProblem ? 500 : 400,
                          }}
                        >
                          {segment.text}
                        </p>
                      </div>
                    );
                  })}
                  
                  {/* Show live transcription progress */}
                  {transcribing && transcript?.chunks_processed && transcript?.total_chunks && (
                    <div className="mt-4 pt-4 border-t border-[#2a2a2a]">
                      <p className="text-xs text-gray-400 text-center">
                        📝 Processing chunk {transcript.chunks_processed} of {transcript.total_chunks}...
                        {transcript.segments?.length > 0 && (
                          <span className="ml-2 text-purple-400">
                            ({transcript.segments.length} segments transcribed)
                          </span>
                        )}
                      </p>
                    </div>
                  )}
                </div>

                {/* Problem & Solution Segments Summary */}
                {(transcript.solution_segments?.length > 0 || transcript.problem_segments?.length > 0) && (
                  <div className="mt-4 pt-4 border-t border-[#2a2a2a]">
                    <p className="text-xs text-gray-400 mb-2">
                      💡 Click on highlighted segments to jump to specific parts
                    </p>
                    <div className="space-y-2">
                      {transcript.solution_segments?.length > 0 && (
                        <>
                          <button
                            onClick={() => {
                              const firstSolution = transcript.solution_segments[0];
                              if (firstSolution < transcript.segments.length) {
                                jumpToTimestamp(transcript.segments[firstSolution].start);
                              }
                            }}
                            className="w-full px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg text-sm font-semibold transition transform hover:scale-105"
                          >
                            ⭐ Jump to First Solution
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
                              className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-semibold transition transform hover:scale-105"
                            >
                              📍 Scroll to Solutions
                            </button>
                          )}
                        </>
                      )}
                      {transcript.problem_segments?.length > 0 && (
                        <button
                          onClick={() => {
                            const firstProblem = transcript.problem_segments[0];
                            if (firstProblem < transcript.segments.length) {
                              jumpToTimestamp(transcript.segments[firstProblem].start);
                            }
                          }}
                          className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-semibold transition transform hover:scale-105"
                        >
                          ❓ Jump to Problem Explanation
                        </button>
                      )}
                    </div>
                    <div className="mt-2 text-xs text-center space-y-1">
                      {transcript.solution_segments?.length > 0 && (
                        <p className="text-yellow-400">
                          ⭐ {transcript.solution_segments.length} solution segment{transcript.solution_segments.length !== 1 ? 's' : ''} found
                        </p>
                      )}
                      {transcript.problem_segments?.length > 0 && (
                        <p className="text-red-400">
                          ❓ {transcript.problem_segments.length} problem segment{transcript.problem_segments.length !== 1 ? 's' : ''} found
                        </p>
                      )}
                    </div>
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

