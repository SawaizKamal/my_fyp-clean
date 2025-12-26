import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import SearchPage from './pages/SearchPage';
import ProcessPage from './pages/ProcessPage';
import ResultPage from './pages/ResultPage';
import ChatPage from './pages/ChatPage';
import VideoPlayerPage from './pages/VideoPlayerPage';
import VideoUploadPage from './pages/VideoUploadPage';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <ErrorBoundary showDetails={process.env.NODE_ENV === 'development'}>
      <AuthProvider>
        <Router>
          <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route 
            path="/search" 
            element={
              <ProtectedRoute>
                <SearchPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/process/:videoId" 
            element={
              <ProtectedRoute>
                <ProcessPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/result/:taskId" 
            element={
              <ProtectedRoute>
                <ResultPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/chat" 
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/video/:videoId" 
            element={
              <ProtectedRoute>
                <VideoPlayerPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/upload-video" 
            element={
              <ProtectedRoute>
                <VideoUploadPage />
              </ProtectedRoute>
            } 
          />
          </Routes>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
