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
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-purple-400">Code Assistant</h1>
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/search')}
              className="text-gray-400 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition"
            >
              Search Videos
            </button>
            <span className="text-gray-400">Welcome, {user?.username}</span>
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

        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="mb-8">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Your Question or Error Message
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Describe your coding problem or paste an error message..."
                  className="w-full px-4 py-3 rounded-xl bg-[#1a1a1a] text-white placeholder-gray-400 border border-[#2a2a2a] focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-purple-600 min-h-[100px] transition"
                  rows="4"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Code (Optional)
                </label>
                <textarea
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Paste your code here for analysis..."
                  className="w-full px-4 py-3 rounded-xl bg-[#1a1a1a] text-white placeholder-gray-400 border border-[#2a2a2a] focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-purple-600 font-mono text-sm min-h-[200px] transition"
                  rows="10"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !message.trim()}
                className="w-full px-8 py-4 bg-purple-600 hover:bg-purple-700 rounded-xl font-semibold transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Analyzing...' : 'Get Help'}
              </button>
            </div>
          </form>

          {error && (
            <div className="bg-red-500 bg-opacity-20 border border-red-500 text-red-300 px-6 py-4 rounded-xl mb-8">
              {error}
            </div>
          )}

          {response && (
            <div className="space-y-6">
              {/* PRIMARY Pattern Badge (Prominent Display) */}
              <div className="flex items-center gap-4">
                <div className="bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 rounded-lg shadow-lg">
                  <span className="font-bold text-lg">🧠 PRIMARY: {response.primary_pattern || response.pattern_name}</span>
                </div>
                <div className="bg-gray-800 px-4 py-2 rounded-lg">
                  <span className="text-sm">Confidence: {response.confidence_score}%</span>
                </div>
              </div>

              {/* Secondary Issues (if any) */}
              {response.secondary_issues && response.secondary_issues.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-gray-400 text-sm">Secondary Issues:</span>
                  {response.secondary_issues.map((issue, index) => (
                    <span key={index} className="bg-yellow-600 bg-opacity-20 border border-yellow-600 px-3 py-1 rounded-full text-xs text-yellow-300">
                      ⚠️ {issue}
                    </span>
                  ))}
                </div>
              )}

              {/* Learning Intent */}
              <div className="bg-blue-500 bg-opacity-10 border border-blue-500 rounded-xl p-4">
                <p className="text-blue-300">
                  <strong>🎯 Learning Goal:</strong> {response.learning_intent}
                </p>
              </div>

              {/* Pattern Explanation */}
              <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6">
                <h2 className="text-xl font-bold text-purple-400 mb-4">💡 Why This Pattern Fails</h2>
                <div className="prose prose-invert max-w-none">
                  <p className="text-gray-300 whitespace-pre-wrap">{response.primary_pattern_explanation || response.pattern_explanation}</p>
                </div>
              </div>

              {/* Debugging Insights */}
              {response.debugging_insight && (
                <div className="bg-red-500 bg-opacity-10 border border-red-500 rounded-xl p-6">
                  <h2 className="text-xl font-bold text-red-400 mb-4">🐛 Debugging Insights</h2>
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-semibold text-red-300 mb-2">🔍 Root Cause:</h3>
                      <p className="text-gray-300">{response.debugging_insight.root_cause}</p>
                    </div>
                    <div>
                      <h3 className="font-semibold text-yellow-300 mb-2">❌ Faulty Assumption:</h3>
                      <p className="text-gray-300">{response.debugging_insight.faulty_assumption}</p>
                    </div>
                    <div>
                      <h3 className="font-semibold text-green-300 mb-2">✅ Correct Flow:</h3>
                      <p className="text-gray-300 whitespace-pre-wrap">{response.debugging_insight.correct_flow}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Corrected Code */}
              {response.corrected_code && (
                <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-purple-400">Corrected Code</h2>
                    <button
                      onClick={() => copyToClipboard(response.corrected_code)}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm transition"
                    >
                      Copy Code
                    </button>
                  </div>
                  <pre className="bg-[#0a0a0a] border border-[#2a2a2a] p-4 rounded-lg overflow-x-auto">
                    <code className="text-sm text-gray-100">{response.corrected_code}</code>
                  </pre>
                </div>
              )}

              {/* GitHub Repositories */}
              {response.github_repos && response.github_repos.length > 0 && (
                <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6">
                  <h2 className="text-xl font-bold text-purple-400 mb-4">🔗 GitHub Repositories</h2>
                  <div className="space-y-3">
                    {response.github_repos.map((repo, index) => (
                      <a
                        key={index}
                        href={repo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block bg-[#1a1a1a] border border-[#2a2a2a] p-4 rounded-lg hover:bg-[#252525] hover:border-purple-600/50 transition"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-white">{repo.name}</h3>
                            <p className="text-sm text-gray-400 mt-1">{repo.description}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-yellow-400">⭐ {repo.stars}</p>
                            <p className="text-xs text-gray-500">{repo.language}</p>
                          </div>
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

              {/* Video Segments with Transcript Display */}
              {response.video_segments && response.video_segments.length > 0 ? (
                <div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6">
                  <h2 className="text-xl font-bold text-purple-400 mb-4">🎥 Pattern-Specific Videos + Transcripts</h2>
                  <div className="space-y-4">
                    {response.video_segments.map((video, index) => (
                      <div key={index} className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4">
                        <div className="flex gap-4">
                          <a href={video.url} target="_blank" rel="noopener noreferrer" className="shrink-0">
                            {video.thumbnail && (
                              <img src={video.thumbnail} alt={video.title} className="w-48 h-32 object-cover rounded" />
                            )}
                          </a>
                          <div className="flex-1">
                            <a href={video.url} target="_blank" rel="noopener noreferrer">
                              <h3 className="font-semibold text-white mb-1 hover:text-purple-400">{video.title}</h3>
                            </a>
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
                        </div>
                        {video.highlighted_portion && (
                          <details className="mt-4">
                            <summary className="cursor-pointer text-sm text-blue-400 hover:text-blue-300 font-semibold">
                              📜 View Transcript (Solution Highlighted ⭐)
                            </summary>
                            <div className="mt-3 p-4 bg-[#0a0a0a] rounded border border-[#2a2a2a] max-h-64 overflow-y-auto">
                              <div className="text-xs font-mono whitespace-pre-wrap leading-relaxed">
                                {video.highlighted_portion.split('\n').map((line, i) => {
                                  const isBold = line.includes('**');
                                  const cleanLine = line.replace(/\*\*/g, '');
                                  return (
                                    <div
                                      key={i}
                                      className={isBold
                                        ? "bg-yellow-500 bg-opacity-20 text-yellow-300 font-bold my-1 px-2 py-1 rounded"
                                        : "text-gray-400 my-1 px-2"}
                                    >
                                      {cleanLine}
                                    </div>
                                  );
                                })}
                              </div>
                              <p className="text-xs text-gray-500 mt-3 italic">
                                💡 Yellow = Key solution moments
                              </p>
                            </div>
                          </details>
                        )}
                      </div>
                    ))}
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
            <div className="text-center text-gray-500 text-xl mt-20">
              Enter your coding question or paste code with errors to get help
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatPage;
