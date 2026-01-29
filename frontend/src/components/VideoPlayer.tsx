import ReactPlayer from "react-player";
import "./VideoPlayer.css";

interface VideoPlayerProps {
  url: string;
  onEnded?: () => void;
  onReady?: () => void;
}

export function VideoPlayer({ url, onEnded, onReady }: VideoPlayerProps) {
  return (
    <div className="video-player-container">
      <ReactPlayer
        src={url}
        width="100%"
        height="100%"
        controls
        onEnded={onEnded}
        onReady={onReady}
        config={{
          vimeo: {
            byline: false,
            portrait: false,
            title: false,
          },
        }}
      />
    </div>
  );
}
