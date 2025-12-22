import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  const handleGetStarted = () => {
    if (isAuthenticated) {
      navigate('/search');
    } else {
      navigate('/login');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700">
      <div className="container mx-auto px-4 py-16">
        {/* Navigation Bar */}
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-2xl font-bold text-white">VideoShortener AI</h2>
          <div className="flex gap-4">
            {isAuthenticated ? (
              <>
                <span className="text-white">Welcome, {user?.username}</span>
                <button
                  onClick={() => navigate('/search')}
                  className="bg-white bg-opacity-20 text-white px-4 py-2 rounded-lg hover:bg-opacity-30 transition"
                >
                  Dashboard
                </button>
                <button
                  onClick={logout}
                  className="bg-white bg-opacity-20 text-white px-4 py-2 rounded-lg hover:bg-opacity-30 transition"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => navigate('/login')}
                  className="bg-white bg-opacity-20 text-white px-4 py-2 rounded-lg hover:bg-opacity-30 transition"
                >
                  Login
                </button>
                <button
                  onClick={() => navigate('/register')}
                  className="bg-white text-purple-600 px-4 py-2 rounded-lg hover:bg-gray-100 transition"
                >
                  Sign Up
                </button>
              </>
            )}
          </div>
        </div>

        <div className="max-w-4xl mx-auto text-center text-white">
          <h1 className="text-6xl font-bold mb-6 animate-fade-in">
            VideoShortener AI
          </h1>
          <p className="text-2xl mb-8 text-gray-200">
            Extract only what matters from YouTube videos
          </p>
          <p className="text-lg mb-12 text-gray-300">
            Powered by AI to find and compile the most relevant parts of any video
          </p>
          
          <button
            onClick={handleGetStarted}
            className="bg-white text-purple-600 font-bold py-4 px-12 rounded-full text-xl hover:bg-gray-100 transition duration-300 transform hover:scale-105 shadow-2xl"
          >
            {isAuthenticated ? 'Go to Dashboard →' : 'Get Started →'}
          </button>
        </div>

        <div className="max-w-6xl mx-auto mt-20 grid md:grid-cols-3 gap-8">
          <div className="bg-white bg-opacity-10 backdrop-blur-lg rounded-2xl p-8 text-white">
            <div className="text-4xl mb-4">🎯</div>
            <h3 className="text-xl font-bold mb-3">Smart Extraction</h3>
            <p className="text-gray-300">
              AI-powered filtering finds exactly what you need from any video
            </p>
          </div>

          <div className="bg-white bg-opacity-10 backdrop-blur-lg rounded-2xl p-8 text-white">
            <div className="text-4xl mb-4">⚡</div>
            <h3 className="text-xl font-bold mb-3">Fast Processing</h3>
            <p className="text-gray-300">
              Get your shortened videos in minutes, not hours
            </p>
          </div>

          <div className="bg-white bg-opacity-10 backdrop-blur-lg rounded-2xl p-8 text-white">
            <div className="text-4xl mb-4">📱</div>
            <h3 className="text-xl font-bold mb-3">Easy to Use</h3>
            <p className="text-gray-300">
              Simple, intuitive interface with no learning curve
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LandingPage;

