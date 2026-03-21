import React, { useState } from "react";

import StartScreen from "./StartScreen";

function App() {
  const [hasStarted, setHasStarted] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(true);

  if (!hasStarted) {
    return (
      <StartScreen
        isAudioMuted={isAudioMuted}
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
