import { useState, useEffect } from 'react';

/**
 * DebugWrapper - A futuristic debugging interface component
 * Used throughout the app for debugging interfaces with neon styling
 */
function DebugWrapper({ title = "Debug Info", data, variant = "default", showTimestamp = true, autoExpand = false }) {
  const [isOpen, setIsOpen] = useState(autoExpand);
  const [timestamp, setTimestamp] = useState(new Date().toISOString());

  useEffect(() => {
    if (showTimestamp) {
      const interval = setInterval(() => {
        setTimestamp(new Date().toISOString());
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [showTimestamp]);

  const variantStyles = {
    default: {
      border: "border-[#00ff41]",
      bg: "bg-[#00ff41]/10",
      text: "text-[#00ff41]",
      glow: "shadow-[0_0_20px_rgba(0,255,65,0.3)]"
    },
    error: {
      border: "border-[#ff0040]",
      bg: "bg-[#ff0040]/10",
      text: "text-[#ff0040]",
      glow: "shadow-[0_0_20px_rgba(255,0,64,0.3)]"
    },
    success: {
      border: "border-[#00ff41]",
      bg: "bg-[#00ff41]/10",
      text: "text-[#00ff41]",
      glow: "shadow-[0_0_20px_rgba(0,255,65,0.3)]"
    },
    warning: {
      border: "border-[#ff00ff]",
      bg: "bg-[#ff00ff]/10",
      text: "text-[#ff00ff]",
      glow: "shadow-[0_0_20px_rgba(255,0,255,0.3)]"
    },
  };

  const styles = variantStyles[variant] || variantStyles.default;

  if (!data && process.env.NODE_ENV !== 'development') return null;

  return (
    <div className={`glass border-2 rounded-lg p-4 ${styles.border} ${styles.bg} ${styles.glow} transition-all duration-300 hover:scale-[1.02] animate-fade-in`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full text-left group"
      >
        <div className="flex items-center gap-3">
          <span className={`font-mono font-bold text-sm ${styles.text} group-hover:animate-neon-glow`}>
            > {title.toUpperCase()}
          </span>
          {showTimestamp && (
            <span className="text-xs text-gray-500 font-mono">
              [{new Date(timestamp).toLocaleTimeString()}]
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-mono ${styles.text}`}>
            {isOpen ? '[EXPANDED]' : '[COLLAPSED]'}
          </span>
          <span className={`text-lg ${styles.text} transition-transform duration-300 ${isOpen ? 'rotate-90' : ''}`}>
            ▶
          </span>
        </div>
      </button>
      
      {isOpen && (
        <div className="mt-4 pt-4 border-t border-current/30 animate-slide-in-left">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-xs font-mono text-gray-400">> DATA STRUCTURE:</span>
            <span className="text-xs font-mono text-[#00ff41]">{typeof data}</span>
          </div>
          <div className="relative">
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-transparent via-transparent to-black/50 pointer-events-none rounded"></div>
            <pre className="text-xs overflow-x-auto bg-black/80 p-4 rounded border border-[#00ff41]/30 font-mono text-[#00ff41] max-h-96 overflow-y-auto relative">
              <code className="whitespace-pre-wrap">{JSON.stringify(data, null, 2)}</code>
            </pre>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs font-mono text-gray-500">
            <span>> SIZE: {JSON.stringify(data).length} bytes</span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(data, null, 2));
                alert('Debug data copied to clipboard!');
              }}
              className="text-[#00ff41] hover:text-[#00ff41] hover:underline transition-colors"
            >
              [COPY DATA]
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default DebugWrapper;

