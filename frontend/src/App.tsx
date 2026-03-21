import React, { useEffect, useState } from "react";

import AudioToggleButton from "./AudioToggleButton";
import GameShell from "./GameShell";
import OpeningAudioPlayer from "./OpeningAudioPlayer";
import StartScreen from "./StartScreen";

declare const __APP_BACKEND_HOST__: string;
declare const __APP_BACKEND_PORT__: string;

const HAS_STARTED_STORAGE_KEY = "grand-pannonia-has-started";

type RoomStateResponse = {
  image_media_type: string;
  room_image_base64: string;
};

function getBackendBaseUrl(): string {
  const configuredBackendUrl = import.meta.env.VITE_BACKEND_URL?.trim();
  if (configuredBackendUrl) {
    return configuredBackendUrl.replace(/\/$/, "");
  }

  const derivedBackendPort = __APP_BACKEND_PORT__.trim();
  if (derivedBackendPort) {
    const derivedBackendHost = __APP_BACKEND_HOST__.trim() || window.location.hostname;
    return `${window.location.protocol}//${derivedBackendHost}:${derivedBackendPort}`;
  }

  return `${window.location.protocol}//${window.location.hostname}:5000`;
}

function App() {
  const [hasStarted, setHasStarted] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.sessionStorage.getItem(HAS_STARTED_STORAGE_KEY) === "true";
  });
  const [isAudioMuted, setIsAudioMuted] = useState(true);
  const [isInventoryOpen, setIsInventoryOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [lobbyImageUrl, setLobbyImageUrl] = useState<string | null>(null);
  const [isLobbyImageLoading, setIsLobbyImageLoading] = useState(true);
  const backendBaseUrl = getBackendBaseUrl();
  const openingThemeUrl = `${backendBaseUrl}/audio/opening-theme`;

  useEffect(() => {
    window.sessionStorage.setItem(HAS_STARTED_STORAGE_KEY, String(hasStarted));
  }, [hasStarted]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadLobbyImage(): Promise<void> {
      try {
        const response = await fetch(`${backendBaseUrl}/rooms/lobby/latest`, {
          credentials: "include",
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`Failed to load lobby image: ${response.status}`);
        }

        const roomState = (await response.json()) as RoomStateResponse;
        setLobbyImageUrl(`data:${roomState.image_media_type};base64,${roomState.room_image_base64}`);
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        console.error("Could not load the lobby image from the backend.", error);
      } finally {
        if (!controller.signal.aborted) {
          setIsLobbyImageLoading(false);
        }
      }
    }

    void loadLobbyImage();

    return () => {
      controller.abort();
    };
  }, [backendBaseUrl]);

  return (
    <>
      <OpeningAudioPlayer audioUrl={openingThemeUrl} isMuted={isAudioMuted} />
      <AudioToggleButton isMuted={isAudioMuted} onToggle={() => setIsAudioMuted((currentValue) => !currentValue)} />

      {hasStarted ? (
        <GameShell
          backgroundImageUrl={lobbyImageUrl}
          isLoadingImage={isLobbyImageLoading}
          isInventoryOpen={isInventoryOpen}
          isChatOpen={isChatOpen}
          onToggleInventory={() => setIsInventoryOpen((currentValue) => !currentValue)}
          onToggleChat={() => setIsChatOpen((currentValue) => !currentValue)}
        />
      ) : (
        <StartScreen
          backgroundImageUrl={lobbyImageUrl}
          isLoadingImage={isLobbyImageLoading}
          onStart={() => setHasStarted(true)}
        />
      )}
    </>
  );
}

export default App;
