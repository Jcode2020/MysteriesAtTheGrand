import React from "react";

type StartScreenProps = {
  backgroundImageUrl: string | null;
  isLoadingImage: boolean;
  isNoticeOpen: boolean;
  hasConsented: boolean;
  onConsentChange: (hasConsented: boolean) => void;
  onCloseNotice: () => void;
  onConfirmStart: () => void;
  onStart: () => void;
};

function StartScreen({
  backgroundImageUrl,
  isLoadingImage,
  isNoticeOpen,
  hasConsented,
  onConsentChange,
  onCloseNotice,
  onConfirmStart,
  onStart,
}: StartScreenProps) {
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

      {isNoticeOpen ? (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-[rgba(18,13,10,0.72)] px-5 backdrop-blur-sm">
          <section className="w-full max-w-3xl rounded-[28px] border border-[#b08a3e]/26 bg-[rgba(28,18,14,0.92)] px-6 py-6 text-left shadow-[0_24px_70px_rgba(0,0,0,0.3)] backdrop-blur-md">
            <p className="text-[11px] uppercase tracking-[0.34em] text-[#e9d8c0]">Prototype Notice</p>
            <h2 className="mt-4 font-display text-[2rem] leading-none text-[#fcf6ee]">Before you enter</h2>
            <div className="mt-4 space-y-3 text-sm leading-7 text-[#f3eadf]">
              <p>This is a prototype. Do not enter any sensitive, personal, financial, or confidential data.</p>
              <p>Your messages and gameplay data will pass through Railway-hosted backend services and OpenAI servers.</p>
            </div>
            <div className="mt-5 border-t border-white/10 pt-5">
              <label className="flex max-w-2xl items-start gap-3 text-sm leading-6 text-[#fcf6ee]">
                <input
                  className="mt-1 h-4 w-4 rounded border border-white/20 bg-transparent accent-[#b08a3e]"
                  type="checkbox"
                  checked={hasConsented}
                  onChange={(event) => onConsentChange(event.target.checked)}
                />
                <span>I understand this prototype warning and agree not to enter sensitive data in the experience.</span>
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                className="rounded-full border border-white/16 px-5 py-3 text-[12px] uppercase tracking-[0.24em] text-[#e9d8c0] transition hover:border-white/24 hover:text-[#fcf6ee]"
                onClick={onCloseNotice}
              >
                Back
              </button>
              <button
                type="button"
                className="rounded-full border border-white/22 bg-[linear-gradient(180deg,rgba(111,36,48,0.96)_0%,rgba(79,23,34,0.98)_100%)] px-6 py-3 text-[12px] uppercase tracking-[0.24em] text-parchment shadow-[0_18px_40px_rgba(0,0,0,0.28)] transition duration-200 hover:-translate-y-px hover:shadow-[0_22px_42px_rgba(0,0,0,0.34)] disabled:cursor-not-allowed disabled:opacity-55"
                onClick={onConfirmStart}
                disabled={!hasConsented}
              >
                Enter
              </button>
            </div>
          </section>
        </div>
      ) : null}

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
