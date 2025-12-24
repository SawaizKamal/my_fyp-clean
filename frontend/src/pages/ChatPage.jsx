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
    <div className="min-h-screen bg-gray-900 text-white">
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
                  className="w-full px-4 py-3 rounded-xl bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 min-h-[100px]"
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
                  className="w-full px-4 py-3 rounded-xl bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono text-sm min-h-[200px]"
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
              <div className="bg-gray-800 rounded-xl p-6">
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
                <div className="bg-gray-800 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-purple-400">Corrected Code</h2>
                    <button
                      onClick={() => copyToClipboard(response.corrected_code)}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm transition"
                    >
                      Copy Code
                    </button>
                  </div>
                  <pre className="bg-gray-900 p-4 rounded-lg overflow-x-auto">
                    <code className="text-sm text-gray-100">{response.corrected_code}</code>
                  </pre>
                </div>
              )}

              {/* GitHub Repositories */}
              {response.github_repos && response.github_repos.length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6">
                  <h2 className="text-xl font-bold text-purple-400 mb-4">🔗 GitHub Repositories</h2>
                  <div className="space-y-3">
                    {response.github_repos.map((repo, index) => (
                      <a
                        key={index}
                        href={repo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block bg-gray-900 p-4 rounded-lg hover:bg-gray-700 transition"
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

              {/* Video Segments with Timestamps */}
              {response.video_segments && response.video_segments.length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6">
                  <h2 className="text-xl font-bold text-purple-400 mb-4">🎥 Pattern-Specific Video Segments</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {response.video_segments.map((video, index) => (
                      <a
                        key={index}
                        href={video.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-gray-900 rounded-lg overflow-hidden hover:bg-gray-700 transition"
                      >
                        {video.thumbnail && (
                          <img
                            src={video.thumbnail}
                            alt={video.title}
                            className="w-full h-40 object-cover"
                          />
                        )}
                        <div className="p-4">
                          <h3 className="font-semibold text-white mb-2 line-clamp-2">
                            {video.title}
                          </h3>
                          <p className="text-sm text-gray-400">{video.channel}</p>
                          {video.relevance_note && (
                            <p className="text-xs text-purple-400 mt-2">🎯 {video.relevance_note}</p>
                          )}
                          {(video.start_time || video.end_time) && (
                            <div className="mt-2 flex gap-2">
                              {video.start_time && (
                                <span className="bg-purple-600 text-xs px-2 py-1 rounded">
                                  {video.start_time}
                                </span>
                              )}
                              {video.end_time && (
                                <span className="bg-purple-600 text-xs px-2 py-1 rounded">
                                  {video.end_time}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </a>
                    ))}
                  </div>
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
