import React from "react";

type AudioToggleButtonProps = {
  isMuted: boolean;
  onToggle: () => void;
};

function AudioOnIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
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
    <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
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

function AudioToggleButton({ isMuted, onToggle }: AudioToggleButtonProps) {
  return (
    <button
      type="button"
      className="fixed right-4 top-4 z-50 inline-flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-black/35 text-parchment shadow-[0_14px_30px_rgba(0,0,0,0.26)] backdrop-blur-md transition duration-200 hover:-translate-y-px hover:bg-black/55 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-parchment md:right-6 md:top-6"
      aria-label={isMuted ? "Turn audio on" : "Turn audio off"}
      aria-pressed={!isMuted}
      onClick={onToggle}
    >
      <span className="sr-only">{isMuted ? "Audio is off" : "Audio is on"}</span>
      {isMuted ? <AudioOffIcon /> : <AudioOnIcon />}
    </button>
  );
}

export default AudioToggleButton;
