import "./VideoPlayer.css";

interface VideoPlayerProps {
  url: string;
  onEnded?: () => void;
  onReady?: () => void;
}

export function VideoPlayer({ url, onEnded, onReady }: VideoPlayerProps) {
  // Extract video ID from YouTube URL
  const getYouTubeId = (url: string) => {
    const match = url.match(/(?:youtu\.be\/|youtube\.com\/watch\?v=|youtube\.com\/embed\/)([^&?/]+)/);
    return match ? match[1] : null;
  };

  const videoId = getYouTubeId(url);

  if (!videoId) {
    return <div className="video-player-container">Invalid video URL</div>;
  }

  return (
    <div className="video-player-container">
      <iframe
        width="100%"
        height="100%"
        src={`https://www.youtube.com/embed/${videoId}`}
        title="Lesson video"
        frameBorder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      />
    </div>
  );
}
