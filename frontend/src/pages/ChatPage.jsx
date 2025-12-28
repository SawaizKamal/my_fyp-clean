import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import chatApi from '../api/chat';

function ChatPage() {
  const [message, setMessage] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [response, setResponse] = useState(null);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const result = await chatApi.chat(message, code || null);
      setResponse(result);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to get response. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
    alert('Code copied to clipboard!');
  };

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 grid-overlay opacity-20"></div>
      <div className="absolute top-0 right-0 w-96 h-96 bg-[#ff00ff] opacity-5 blur-3xl animate-float"></div>
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-[#00ff41] opacity-5 blur-3xl animate-float" style={{ animationDelay: '1s' }}></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        <div className="flex items-center justify-between mb-8 animate-slide-in-left">
          <h1 className="text-4xl font-black neon-text-green font-mono uppercase tracking-wider animate-neon-glow">you-solution</h1>
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/upload-video')}
              className="glass border border-[#ff00ff] text-[#ff00ff] hover:bg-[#ff00ff] hover:text-black px-4 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm uppercase"
            >
              > UPLOAD VIDEO
            </button>
            <button
              onClick={() => navigate('/search')}
              className="glass border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black px-4 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm uppercase"
            >
              > SEARCH
            </button>
            <span className="text-gray-300 font-mono text-sm">[ {user?.username} ]</span>
            <button
              onClick={() => navigate('/')}
              className="glass border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black px-4 py-2 rounded-lg transition-all duration-300 cyber-button font-mono text-sm uppercase"
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

        <div className="max-w-4xl mx-auto animate-fade-in">
          {/* Info Banner */}
          <div className="glass-neon border-2 border-[#00ff41] rounded-xl p-4 mb-6 animate-slide-in-left" style={{ boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)' }}>
            <p className="text-[#00ff41] text-sm font-mono">
              > <strong>NEW FEATURE:</strong> Upload your own video and get AI-powered transcription with solution highlighting! 
              <button
                onClick={() => navigate('/upload-video')}
                className="ml-2 underline hover:text-[#ff00ff] transition-colors font-bold"
              >
                TRY IT NOW →
              </button>
            </p>
          </div>
          
          <form onSubmit={handleSubmit} className="mb-8">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-[#ff00ff] mb-2 font-mono uppercase">
                  > YOUR QUESTION OR ERROR MESSAGE
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Describe your coding problem or paste an error message..."
                  className="w-full px-4 py-3 rounded-xl bg-black/80 text-[#00ff41] placeholder-gray-500 border-2 border-[#ff00ff] focus:outline-none focus:ring-2 focus:ring-[#ff00ff] focus:border-[#ff00ff] min-h-[100px] transition-all duration-300 font-mono text-sm focus:shadow-[0_0_20px_rgba(255,0,255,0.3)]"
                  rows="4"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-[#00ff41] mb-2 font-mono uppercase">
                  > CODE (OPTIONAL)
                </label>
                <textarea
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Paste your code here for analysis..."
                  className="w-full px-4 py-3 rounded-xl bg-black/80 text-[#00ff41] placeholder-gray-500 border-2 border-[#00ff41] focus:outline-none focus:ring-2 focus:ring-[#00ff41] focus:border-[#00ff41] font-mono text-sm min-h-[200px] transition-all duration-300 focus:shadow-[0_0_20px_rgba(0,255,65,0.3)]"
                  rows="10"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !message.trim()}
                className="w-full px-8 py-5 bg-gradient-to-r from-[#ff0040] via-[#ff00ff] to-[#00ff41] hover:from-[#ff00ff] hover:via-[#00ff41] hover:to-[#ff0040] rounded-xl font-black transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed cyber-button font-mono text-lg uppercase tracking-wider transform hover:scale-105 disabled:transform-none"
                style={{ boxShadow: '0 0 30px rgba(255, 0, 64, 0.5), 0 0 60px rgba(255, 0, 255, 0.3)' }}
              >
                {loading ? '> ANALYZING...' : '> GET HELP'}
              </button>
            </div>
          </form>

          {error && (
            <div className="glass border-2 border-[#ff0040] text-[#ff0040] px-6 py-4 rounded-xl mb-8 animate-slide-in-left font-mono" style={{ boxShadow: '0 0 20px rgba(255, 0, 64, 0.5)' }}>
              <div className="flex items-center gap-2 font-bold">
                <span>> ERROR:</span>
                <span className="font-normal">{error}</span>
              </div>
            </div>
          )}

          {response && (
            <div className="space-y-6 animate-fade-in">
              {/* PRIMARY Pattern Badge (Prominent Display) */}
              <div className="flex items-center gap-4">
                <div className="glass-neon border-2 border-[#00ff41] px-6 py-3 rounded-lg shadow-[0_0_30px_rgba(0,255,65,0.5)]">
                  <span className="font-black text-lg font-mono neon-text-green uppercase">🧠 PRIMARY: {response.primary_pattern || response.pattern_name}</span>
                </div>
                <div className="glass border border-[#ff00ff] px-4 py-2 rounded-lg">
                  <span className="text-sm font-mono font-bold text-[#ff00ff]">CONFIDENCE: {response.confidence_score}%</span>
                </div>
              </div>

              {/* Secondary Issues (if any) */}
              {response.secondary_issues && response.secondary_issues.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-gray-400 text-sm font-mono">> SECONDARY ISSUES:</span>
                  {response.secondary_issues.map((issue, index) => (
                    <span key={index} className="glass border border-[#ff00ff] px-3 py-1 rounded-full text-xs text-[#ff00ff] font-mono font-bold">
                      ⚠️ {issue}
                    </span>
                  ))}
                </div>
              )}

              {/* Learning Intent */}
              <div className="glass border-2 border-[#00ff41] rounded-xl p-4" style={{ boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)' }}>
                <p className="text-[#00ff41] font-mono">
                  <strong className="font-black">> 🎯 LEARNING GOAL:</strong> <span className="font-normal">{response.learning_intent}</span>
                </p>
              </div>

              {/* Pattern Explanation */}
              <div className="glass-neon rounded-xl p-6 border-2">
                <h2 className="text-xl font-black neon-text-green mb-4 font-mono uppercase tracking-wider">💡 WHY THIS PATTERN FAILS</h2>
                <div className="prose prose-invert max-w-none">
                  <p className="text-gray-300 whitespace-pre-wrap font-mono text-sm leading-relaxed">{response.primary_pattern_explanation || response.pattern_explanation}</p>
                </div>
              </div>

              {/* Debugging Insights */}
              {response.debugging_insight && (
                <div className="glass border-2 border-[#ff0040] rounded-xl p-6" style={{ boxShadow: '0 0 20px rgba(255, 0, 64, 0.3)' }}>
                  <h2 className="text-xl font-black neon-text-red mb-4 font-mono uppercase tracking-wider">🐛 DEBUGGING INSIGHTS</h2>
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-bold text-[#ff0040] mb-2 font-mono">> 🔍 ROOT CAUSE:</h3>
                      <p className="text-gray-300 font-mono text-sm">{response.debugging_insight.root_cause}</p>
                    </div>
                    <div>
                      <h3 className="font-bold text-[#ff00ff] mb-2 font-mono">> ❌ FAULTY ASSUMPTION:</h3>
                      <p className="text-gray-300 font-mono text-sm">{response.debugging_insight.faulty_assumption}</p>
                    </div>
                    <div>
                      <h3 className="font-bold text-[#00ff41] mb-2 font-mono">> ✅ CORRECT FLOW:</h3>
                      <p className="text-gray-300 whitespace-pre-wrap font-mono text-sm">{response.debugging_insight.correct_flow}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Corrected Code */}
              {response.corrected_code && (
                <div className="glass-neon rounded-xl p-6 border-2">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-black neon-text-green font-mono uppercase tracking-wider">CORRECTED CODE</h2>
                    <button
                      onClick={() => copyToClipboard(response.corrected_code)}
                      className="px-4 py-2 glass border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41] hover:text-black rounded-lg text-sm transition-all duration-300 cyber-button font-mono font-bold uppercase"
                    >
                      > COPY CODE
                    </button>
                  </div>
                  <pre className="bg-black/80 border-2 border-[#00ff41] p-4 rounded-lg overflow-x-auto font-mono" style={{ boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)' }}>
                    <code className="text-sm text-[#00ff41]">{response.corrected_code}</code>
                  </pre>
                </div>
              )}

              {/* GitHub Repositories - Compact Display (Name, Stars, Language Only) */}
              {response.github_repos && response.github_repos.length > 0 && (
                <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6">
                  <h2 className="text-xl font-bold text-purple-400 mb-4">🔗 GitHub Repositories</h2>
                  <div className="space-y-2">
                    {response.github_repos.map((repo, index) => (
                      <a
                        key={index}
                        href={repo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between bg-[#1a1a1a] border border-[#2a2a2a] px-4 py-3 rounded-lg hover:bg-[#252525] hover:border-purple-600/50 transition group"
                      >
                        <div className="flex-1 min-w-0">
                          <span className="font-medium text-purple-400 group-hover:text-purple-300 text-sm block truncate">
                            {repo.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-xs ml-4 shrink-0">
                          <span className="text-yellow-400">⭐ {repo.stars}</span>
                          <span className="text-gray-500 bg-[#0a0a0a] px-2 py-1 rounded">{repo.language}</span>
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* StackOverflow Threads */}
              {response.stackoverflow_links && response.stackoverflow_links.length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6">
                  <h2 className="text-xl font-bold text-purple-400 mb-4">💬 StackOverflow Discussions</h2>
                  <ul className="space-y-3">
                    {response.stackoverflow_links.map((thread, index) => (
                      <li key={index}>
                        <a
                          href={thread.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block bg-gray-900 p-3 rounded-lg hover:bg-gray-700 transition"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-purple-400 hover:text-purple-300">{thread.title}</span>
                            <div className="flex gap-3 text-sm text-gray-400">
                              <span>⬆ {thread.score}</span>
                              <span>💬 {thread.answer_count}</span>
                            </div>
                          </div>
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Dev.to Articles */}
              {response.dev_articles && response.dev_articles.length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6">
                  <h2 className="text-xl font-bold text-purple-400 mb-4">📝 Dev Articles</h2>
                  <ul className="space-y-2">
                    {response.dev_articles.map((article, index) => (
                      <li key={index}>
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block bg-gray-900 p-3 rounded-lg hover:bg-gray-700 transition"
                        >
                          <h3 className="text-purple-400 hover:text-purple-300">{article.title}</h3>
                          <p className="text-xs text-gray-500 mt-1">by {article.author}</p>
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Video Segments with Embedded Player and Transcript Display */}
              {response.video_segments && response.video_segments.length > 0 ? (
                <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6">
                  <h2 className="text-xl font-bold text-purple-400 mb-4">🎥 Pattern-Specific Videos + Transcripts</h2>
                  <div className="space-y-6">
                    {response.video_segments.map((video, index) => {
                      // Extract video ID from URL if not provided
                      const videoId = video.video_id || (video.url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?]*)/)?.[1] || '');
                      
                      // Parse start time (format: MM:SS or seconds)
                      let startSeconds = 0;
                      if (video.start_time) {
                        const timeParts = video.start_time.split(':');
                        if (timeParts.length === 2) {
                          startSeconds = parseInt(timeParts[0]) * 60 + parseInt(timeParts[1]);
                        } else {
                          startSeconds = parseInt(video.start_time) || 0;
                        }
                      }
                      
                      const embedUrl = videoId ? `https://www.youtube.com/embed/${videoId}${startSeconds > 0 ? `?start=${startSeconds}` : ''}` : null;
                      
                      return (
                        <div key={index} className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4">
                          <div className="mb-4">
                            <h3 className="font-semibold text-white mb-2">{video.title}</h3>
                            <p className="text-sm text-gray-400 mb-2">{video.channel}</p>
                            {video.relevance_note && (
                              <p className="text-xs text-purple-400 mb-2">🎯 {video.relevance_note}</p>
                            )}
                            {(video.start_time && video.end_time) && (
                              <span className="bg-green-600 text-xs px-3 py-1 rounded font-mono">
                                ⏱️ {video.start_time} - {video.end_time}
                              </span>
                            )}
                          </div>
                          
                          {/* Action Button - Open with Live Transcription */}
                          {videoId && (
                            <div className="mb-4">
                              <button
                                onClick={() => navigate(`/video/${videoId}`)}
                                className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 rounded-lg font-semibold transition duration-200 flex items-center justify-center gap-2"
                              >
                                <span>🎬</span>
                                <span>Open with Live Transcription & Solution Highlighting</span>
                                <span>→</span>
                              </button>
                              <p className="text-xs text-gray-500 mt-2 text-center">
                                Get full transcript with timestamps and jump directly to solution parts
                              </p>
                            </div>
                          )}

                          {/* Embedded YouTube Player */}
                          {embedUrl ? (
                            <div className="mb-4 bg-black rounded-lg overflow-hidden">
                              <iframe
                                width="100%"
                                height="400"
                                src={embedUrl}
                                title={video.title}
                                frameBorder="0"
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowFullScreen
                                className="w-full"
                              ></iframe>
                            </div>
                          ) : (
                            <div className="mb-4 bg-[#0a0a0a] rounded-lg p-4 border border-[#2a2a2a]">
                              <p className="text-gray-400 text-sm">Video player unavailable</p>
                              <a href={video.url} target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 text-sm">
                                Open in YouTube →
                              </a>
                            </div>
                          )}
                          
                          {/* Transcript with Solution Highlighting */}
                          {video.highlighted_portion && (
                            <details className="mt-4" open>
                              <summary className="cursor-pointer text-sm text-blue-400 hover:text-blue-300 font-semibold mb-2">
                                📜 View Transcript (Solution Highlighted ⭐)
                              </summary>
                              <div className="mt-3 p-4 bg-[#0a0a0a] rounded border border-[#2a2a2a] max-h-96 overflow-y-auto">
                                <div className="text-xs font-mono whitespace-pre-wrap leading-relaxed">
                                  {video.highlighted_portion.split('\n').map((line, i) => {
                                    const isBold = line.includes('**');
                                    const cleanLine = line.replace(/\*\*/g, '');
                                    return (
                                      <div
                                        key={i}
                                        className={isBold
                                          ? "bg-yellow-500 bg-opacity-30 border-l-4 border-yellow-500 text-yellow-200 font-bold my-2 px-3 py-2 rounded-r"
                                          : "text-gray-400 my-1 px-2"}
                                      >
                                        {cleanLine}
                                      </div>
                                    );
                                  })}
                                </div>
                                <p className="text-xs text-gray-500 mt-3 italic border-t border-[#2a2a2a] pt-3">
                                  💡 <strong>Yellow highlighted sections</strong> = Key solution moments where the pattern is explained
                                </p>
                              </div>
                            </details>
                          )}
                          
                          {/* Full Transcript (if available and different from highlighted) */}
                          {video.transcript_text && video.transcript_text !== video.highlighted_portion && (
                            <details className="mt-2">
                              <summary className="cursor-pointer text-sm text-gray-400 hover:text-gray-300 text-xs">
                                📄 View Full Transcript
                              </summary>
                              <div className="mt-2 p-3 bg-[#0a0a0a] rounded border border-[#2a2a2a] max-h-64 overflow-y-auto text-xs text-gray-400 font-mono">
                                <pre className="whitespace-pre-wrap">{video.transcript_text}</pre>
                              </div>
                            </details>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  {response.video_skip_reasons && response.video_skip_reasons.length > 0 && (
                    <details className="mt-4">
                      <summary className="cursor-pointer text-sm text-yellow-400 hover:text-yellow-300">
                        ⚠️ {response.video_skip_reasons.length} video(s) skipped (click to see reasons)
                      </summary>
                      <ul className="mt-2 text-xs text-gray-400 space-y-1">
                        {response.video_skip_reasons.map((reason, i) => (
                          <li key={i}>• {reason}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              ) : response && (
                <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6">
                  <h2 className="text-xl font-bold text-purple-400 mb-4">🎥 Pattern-Specific Videos</h2>
                  <p className="text-gray-400">
                    No videos found for this pattern. This might be because:
                  </p>
                  <ul className="list-disc list-inside text-sm text-gray-400 mt-2 space-y-1">
                    <li>YouTube API key is not configured (set YOUTUBE_API_KEY)</li>
                    <li>No videos match this specific pattern</li>
                    <li>Videos found don't have available transcripts</li>
                  </ul>
                  {response.video_skip_reasons && response.video_skip_reasons.length > 0 && (
                    <details className="mt-4">
                      <summary className="cursor-pointer text-sm text-yellow-400 hover:text-yellow-300">
                        ⚠️ See skipped videos ({response.video_skip_reasons.length})
                      </summary>
                      <ul className="mt-2 text-xs text-gray-400 space-y-1">
                        {response.video_skip_reasons.map((reason, i) => (
                          <li key={i}>• {reason}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              )}
            </div>
          )}

          {!response && !loading && !error && (
            <div className="text-center text-gray-400 text-xl mt-20 font-mono animate-fade-in">
              > ENTER YOUR CODING QUESTION OR PASTE CODE WITH ERRORS TO GET HELP
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatPage;
