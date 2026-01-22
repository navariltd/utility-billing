const AspectRatioVideo = ({
  videoUrl,
  aspectRatio = "video", // Default aspect ratio
  title = "Embedded Video",
}) => {
  return (
    <div className={`aspect-${aspectRatio} overflow-hidden rounded-lg`}>
      <iframe
        src={videoUrl}
        title={title}
        frameBorder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        className="w-full h-full"
      ></iframe>
    </div>
  );
};

export default AspectRatioVideo;
