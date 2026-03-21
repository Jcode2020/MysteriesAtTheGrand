import React from "react";

type StartScreenProps = {
  backgroundImageUrl: string | null;
  isLoadingImage: boolean;
  onStart: () => void;
};

function StartScreen({ backgroundImageUrl, isLoadingImage, onStart }: StartScreenProps) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#120d0a] text-parchment">
      {backgroundImageUrl ? (
        <img
          className="absolute inset-0 h-full w-full scale-[1.02] object-cover object-center"
          src={backgroundImageUrl}
          alt="Grand hotel lobby with warm chandelier light, marble floors, and a sweeping staircase."
        />
      ) : null}

      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(20,14,11,0.34)_0%,rgba(20,14,11,0.5)_35%,rgba(20,14,11,0.72)_100%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(20,14,11,0.18)_44%,rgba(20,14,11,0.62)_100%)]" />

      <section
        className="relative z-10 grid min-h-screen justify-items-center px-5 py-6"
        aria-labelledby="start-screen-title"
        style={{ gridTemplateRows: "1fr auto" }}
      >
        <div className="mt-[min(10dvh,5rem)] self-center text-center drop-shadow-[0_10px_28px_rgba(0,0,0,0.38)]">
          <p className="mb-3 text-[clamp(0.8rem,1vw+0.65rem,1rem)] uppercase tracking-[0.32em] text-white/82">
            Welcome to
          </p>
          <h1
            id="start-screen-title"
            className="mx-auto max-w-[10ch] font-display text-[clamp(2.9rem,7vw,5.75rem)] leading-[1.02]"
          >
            Grand Pannonia Hotel
          </h1>
          {isLoadingImage ? (
            <p className="mt-4 text-[0.82rem] uppercase tracking-[0.16em] text-white/74">Preparing the lobby...</p>
          ) : null}
        </div>

        <button
          type="button"
          className="mb-[clamp(2rem,9dvh,4.75rem)] min-h-14 min-w-[min(18rem,calc(100vw-3rem))] rounded-full border border-white/22 bg-[linear-gradient(180deg,rgba(111,36,48,0.96)_0%,rgba(79,23,34,0.98)_100%)] px-8 py-4 text-base font-medium uppercase tracking-[0.34em] text-parchment shadow-[0_18px_40px_rgba(0,0,0,0.28)] transition duration-200 hover:-translate-y-px hover:shadow-[0_22px_42px_rgba(0,0,0,0.34)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-parchment"
          onClick={onStart}
        >
          Start
        </button>
      </section>
    </main>
  );
}

export default StartScreen;
