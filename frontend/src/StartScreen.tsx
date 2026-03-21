import React, { useCallback, useEffect, useRef } from "react";

type StartScreenProps = {
  audioUrl: string;
  backgroundImageUrl: string | null;
  isAudioMuted: boolean;
  isLoadingImage: boolean;
  onStart: () => void;
  onToggleAudio: () => void;
};

function AudioOnIcon() {
  return (
    <svg aria-hidden="true" className="audio-toggle__icon" viewBox="0 0 24 24">
      <path
        d="M5 14.5V9.5H8.5L13 5.75V18.25L8.5 14.5H5Z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
      <path
        d="M16 9C17.3 10.1 18 11.47 18 13C18 14.53 17.3 15.9 16 17"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
      <path
        d="M18 6.5C20 8.2 21 10.37 21 13C21 15.63 20 17.8 18 19.5"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
    </svg>
  );
}

function AudioOffIcon() {
  return (
    <svg aria-hidden="true" className="audio-toggle__icon" viewBox="0 0 24 24">
      <path
        d="M5 14.5V9.5H8.5L13 5.75V18.25L8.5 14.5H5Z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
      <path
        d="M16 9L21 17"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
      <path
        d="M21 9L16 17"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
    </svg>
  );
}

function StartScreen({
  audioUrl,
  backgroundImageUrl,
  isAudioMuted,
  isLoadingImage,
  onStart,
  onToggleAudio,
}: StartScreenProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const shouldKeepTryingToPlayRef = useRef(!isAudioMuted);

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
    if (audioElement === null) {
      return;
    }

    if (isAudioMuted) {
      shouldKeepTryingToPlayRef.current = false;
      audioElement.muted = true;
      audioElement.pause();
      return;
    }

    shouldKeepTryingToPlayRef.current = true;
    audioElement.muted = false;
    attemptPlayback();
  }, [attemptPlayback, audioUrl, isAudioMuted]);

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

  return (
    <main className="start-screen">
      <audio
        ref={audioRef}
        src={audioUrl}
        loop
        preload="auto"
        autoPlay
        playsInline
        onCanPlayThrough={attemptPlayback}
        aria-hidden="true"
      />

      {backgroundImageUrl ? (
        <img
          className="start-screen__background"
          src={backgroundImageUrl}
          alt="Grand hotel lobby with warm chandelier light, marble floors, and a sweeping staircase."
        />
      ) : null}

      <div className="start-screen__overlay" />

      <button
        type="button"
        className="audio-toggle"
        aria-label={isAudioMuted ? "Turn audio on" : "Turn audio off"}
        aria-pressed={!isAudioMuted}
        onClick={onToggleAudio}
      >
        <span className="sr-only">{isAudioMuted ? "Audio is off" : "Audio is on"}</span>
        {isAudioMuted ? <AudioOffIcon /> : <AudioOnIcon />}
      </button>

      <section className="start-screen__content" aria-labelledby="start-screen-title">
        <div className="start-screen__title-wrap">
          <p className="start-screen__eyebrow">Welcome to</p>
          <h1 id="start-screen-title" className="start-screen__title">
            Grand Pannonia Hotel
          </h1>
          {isLoadingImage ? <p className="start-screen__status">Preparing the lobby...</p> : null}
        </div>

        <button type="button" className="start-screen__button" onClick={onStart}>
          START
        </button>
      </section>
    </main>
  );
}

export default StartScreen;
