import React, { useEffect, useState } from "react";

import StartScreen from "./StartScreen";

declare const __APP_BACKEND_HOST__: string;
declare const __APP_BACKEND_PORT__: string;

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
  const [hasStarted, setHasStarted] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(true);
  const [lobbyImageUrl, setLobbyImageUrl] = useState<string | null>(null);
  const [isLobbyImageLoading, setIsLobbyImageLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    const backendBaseUrl = getBackendBaseUrl();

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
  }, []);

  if (!hasStarted) {
    return (
      <StartScreen
        backgroundImageUrl={lobbyImageUrl}
        isAudioMuted={isAudioMuted}
        isLoadingImage={isLobbyImageLoading}
        onStart={() => setHasStarted(true)}
        onToggleAudio={() => setIsAudioMuted((currentValue) => !currentValue)}
      />
    );
  }

  return (
    <main className="app-shell">
      <section className="app-placeholder" aria-labelledby="game-placeholder-title">
        <p className="app-placeholder__eyebrow">Grand Pannonia Hotel</p>
        <h1 id="game-placeholder-title">The mystery awaits behind the lobby doors.</h1>
        <p className="app-placeholder__copy">
          The welcome screen is now active. The next step is to connect this state to the first playable
          scene.
        </p>
      </section>
    </main>
  );
}

export default App;
