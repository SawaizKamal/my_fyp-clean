import React from 'react';

/**
 * ErrorBoundary - Catches React errors and displays a friendly error message
 * Wraps components to prevent the entire app from crashing
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center p-4">
          <div className="max-w-2xl w-full bg-[#111111] border border-red-500/50 rounded-xl p-8">
            <h1 className="text-2xl font-bold text-red-400 mb-4">
              ⚠️ Something went wrong
            </h1>
            <p className="text-gray-300 mb-6">
              An unexpected error occurred. Please try refreshing the page or contact support if the problem persists.
            </p>
            
            {this.props.showDetails && this.state.error && (
              <details className="mt-4">
                <summary className="cursor-pointer text-sm text-gray-400 hover:text-gray-300 mb-2">
                  Error Details
                </summary>
                <div className="bg-[#0a0a0a] border border-[#2a2a2a] rounded p-4 text-xs overflow-x-auto">
                  <p className="text-red-400 font-mono mb-2">
                    {this.state.error.toString()}
                  </p>
                  <pre className="text-gray-400">
                    {this.state.errorInfo?.componentStack}
                  </pre>
                </div>
              </details>
            )}
            
            <button
              onClick={() => window.location.reload()}
              className="mt-6 px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold transition"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

