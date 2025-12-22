function VideoCard({ video, onClick }) {
  return (
    <div
      onClick={onClick}
      className="bg-gray-800 rounded-xl overflow-hidden cursor-pointer hover:scale-105 transition duration-200 shadow-lg hover:shadow-2xl"
    >
      <img
        src={video.thumbnail}
        alt={video.title}
        className="w-full aspect-video object-cover"
      />
      <div className="p-4">
        <h3 className="font-semibold text-white mb-2 line-clamp-2">
          {video.title}
        </h3>
        <p className="text-sm text-gray-400 mb-2">{video.channel}</p>
        <p className="text-xs text-gray-500 line-clamp-2">
          {video.description}
        </p>
      </div>
    </div>
  );
}

export default VideoCard;

