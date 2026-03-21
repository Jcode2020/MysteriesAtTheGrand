import React, { useCallback, useEffect, useRef } from "react";

type OpeningAudioPlayerProps = {
  audioUrl: string | null;
  isMuted: boolean;
  volume: number;
};

function OpeningAudioPlayer({ audioUrl, isMuted, volume }: OpeningAudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const shouldKeepTryingToPlayRef = useRef(!isMuted);

  const attemptPlayback = useCallback(() => {
    const audioElement = audioRef.current;
    if (audioElement === null || shouldKeepTryingToPlayRef.current === false) {
      return;
    }

    void audioElement.play().catch((error: unknown) => {
      console.warn("Opening theme autoplay was blocked by the browser.", error);
    });
  }, []);

  useEffect(() => {
    const audioElement = audioRef.current;
    if (audioElement === null || !audioUrl) {
      return;
    }

    // Keep the looping theme duckable while narrated overlays take focus.
    audioElement.volume = Math.min(Math.max(volume, 0), 1);
  }, [audioUrl, volume]);

  useEffect(() => {
    const audioElement = audioRef.current;
    if (audioElement === null || !audioUrl) {
      return;
    }

    if (isMuted) {
      shouldKeepTryingToPlayRef.current = false;
      audioElement.muted = true;
      audioElement.pause();
      return;
    }

    shouldKeepTryingToPlayRef.current = true;
    audioElement.muted = false;
    attemptPlayback();
  }, [attemptPlayback, audioUrl, isMuted]);

  useEffect(() => {
    function resumeAudioFromFirstInteraction() {
      attemptPlayback();
    }

    window.addEventListener("pointerdown", resumeAudioFromFirstInteraction);
    window.addEventListener("keydown", resumeAudioFromFirstInteraction);

    return () => {
      window.removeEventListener("pointerdown", resumeAudioFromFirstInteraction);
      window.removeEventListener("keydown", resumeAudioFromFirstInteraction);
    };
  }, [attemptPlayback]);

  if (!audioUrl) {
    return null;
  }

  return (
    <audio
      ref={audioRef}
      src={audioUrl}
      loop
      preload="auto"
      autoPlay
      playsInline
      onCanPlayThrough={attemptPlayback}
      aria-hidden="true"
      className="hidden"
    />
  );
}

export default OpeningAudioPlayer;
