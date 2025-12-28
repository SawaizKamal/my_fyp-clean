/**
 * LoadingSpinner - Futuristic loading spinner component with neon variants
 */
function LoadingSpinner({ size = "md", variant = "green" }) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
    xl: "w-16 h-16",
  };

  const variantClasses = {
    green: "border-[#00ff41]",
    pink: "border-[#ff00ff]",
    red: "border-[#ff0040]",
    white: "border-white",
  };

  const glowClasses = {
    green: "shadow-[0_0_20px_rgba(0,255,65,0.5)]",
    pink: "shadow-[0_0_20px_rgba(255,0,255,0.5)]",
    red: "shadow-[0_0_20px_rgba(255,0,64,0.5)]",
    white: "shadow-[0_0_20px_rgba(255,255,255,0.3)]",
  };

  return (
    <div className="flex items-center justify-center relative">
      <div
        className={`${sizeClasses[size]} ${variantClasses[variant]} border-4 border-t-transparent rounded-full animate-spin ${glowClasses[variant]}`}
      ></div>
      <div
        className={`absolute ${sizeClasses[size]} ${variantClasses[variant === 'green' ? 'pink' : variant === 'pink' ? 'red' : 'green']} border-4 border-t-transparent rounded-full animate-spin`}
        style={{ animationDirection: 'reverse', animationDuration: '1.5s', opacity: 0.5 }}
      ></div>
    </div>
  );
}

export default LoadingSpinner;

