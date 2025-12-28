function VideoCard({ video, onClick }) {
  return (
    <div
      onClick={onClick}
      className="glass border-2 border-[#00ff41] rounded-xl overflow-hidden cursor-pointer hover:scale-105 transition-all duration-300 shadow-[0_0_20px_rgba(0,255,65,0.3)] hover:shadow-[0_0_30px_rgba(0,255,65,0.5)] hover:border-[#ff00ff] animate-fade-in cyber-button"
    >
      <div className="relative">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="w-full aspect-video object-cover"
        />
        <div className="absolute top-2 right-2 glass border border-[#ff00ff] px-2 py-1 rounded text-xs font-mono font-bold text-[#ff00ff]">
          > VIDEO
        </div>
      </div>
      <div className="p-4">
        <h3 className="font-bold text-[#00ff41] mb-2 line-clamp-2 font-mono text-sm uppercase">
          {video.title}
        </h3>
        <p className="text-sm text-gray-300 mb-2 font-mono">{video.channel}</p>
        <p className="text-xs text-gray-400 line-clamp-2 font-mono">
          {video.description}
        </p>
      </div>
    </div>
  );
}

export default VideoCard;

