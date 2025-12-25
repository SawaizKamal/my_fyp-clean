import { useState } from 'react';

/**
 * DebugWrapper - A component for displaying debugging information in a collapsible panel
 * Used throughout the app for debugging interfaces
 */
function DebugWrapper({ title = "Debug Info", data, variant = "default" }) {
  const [isOpen, setIsOpen] = useState(false);

  const variantStyles = {
    default: "bg-blue-500/10 border-blue-500/50",
    error: "bg-red-500/10 border-red-500/50",
    success: "bg-green-500/10 border-green-500/50",
    warning: "bg-yellow-500/10 border-yellow-500/50",
  };

  if (!data) return null;

  return (
    <div className={`border rounded-lg p-4 ${variantStyles[variant]}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full text-left"
      >
        <span className="font-semibold text-sm">
          🔍 {title}
        </span>
        <span className="text-xs opacity-70">
          {isOpen ? '▼' : '▶'}
        </span>
      </button>
      
      {isOpen && (
        <div className="mt-4 pt-4 border-t border-current/20">
          <pre className="text-xs overflow-x-auto bg-[#0a0a0a] p-3 rounded border border-[#2a2a2a]">
            <code>{JSON.stringify(data, null, 2)}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

export default DebugWrapper;

