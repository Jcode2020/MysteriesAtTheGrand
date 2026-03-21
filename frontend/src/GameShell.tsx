import React from "react";

type GameShellProps = {
  backgroundImageUrl: string | null;
  isLoadingImage: boolean;
  isInventoryOpen: boolean;
  isChatOpen: boolean;
  onToggleInventory: () => void;
  onToggleChat: () => void;
};

type MockInventoryItem = {
  detail: string;
  mark: string;
  name: string;
};

const INVENTORY_ITEMS: MockInventoryItem[] = [
  { name: "Pen", mark: "P", detail: "Reception Desk" },
  { name: "Book", mark: "B", detail: "Guest Library" },
  { name: "Contract", mark: "C", detail: "Signed Copy" },
  { name: "Cash", mark: "$", detail: "Tucked Away" },
  { name: "Teddy", mark: "T", detail: "Nursery Find" },
  { name: "Watch", mark: "W", detail: "Pocket Piece" },
  { name: "Scarf", mark: "S", detail: "Velvet Clue" },
];

function SuitcaseIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
      <path
        d="M8.25 7.25V5.75C8.25 4.92 8.92 4.25 9.75 4.25H14.25C15.08 4.25 15.75 4.92 15.75 5.75V7.25"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
      <rect
        x="4.25"
        y="7.25"
        width="15.5"
        height="12.5"
        rx="2.25"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
      <path
        d="M4.25 12H19.75"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
      <path
        d="M6.25 8.25C6.25 6.59 7.59 5.25 9.25 5.25H17.25C18.91 5.25 20.25 6.59 20.25 8.25V13.25C20.25 14.91 18.91 16.25 17.25 16.25H12L8.25 19V16.25H9.25C7.59 16.25 6.25 14.91 6.25 13.25V8.25Z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
      <path
        d="M10 10.75H16.5"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
      <path
        d="M10 13.25H14.5"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function GameShell({
  backgroundImageUrl,
  isLoadingImage,
  isInventoryOpen,
  isChatOpen,
  onToggleInventory,
  onToggleChat,
}: GameShellProps) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#120d0a] text-parchment">
      {backgroundImageUrl ? (
        <img
          className="absolute inset-0 h-full w-full object-cover object-center opacity-45 blur-[2px] scale-[1.03]"
          src={backgroundImageUrl}
          alt=""
          aria-hidden="true"
        />
      ) : null}

      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(20,14,11,0.24)_0%,rgba(20,14,11,0.5)_45%,rgba(20,14,11,0.8)_100%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(20,14,11,0.14)_40%,rgba(20,14,11,0.5)_100%)]" />

      {isInventoryOpen ? (
        <aside className="absolute bottom-8 left-8 top-24 z-30 flex w-[22rem] flex-col rounded-[28px] border border-[#b08a3e]/35 bg-[rgba(252,246,238,0.92)] p-6 text-walnut-ink shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur-md">
          <p className="text-[11px] uppercase tracking-[0.34em] text-[#6f584b]">Travel Effects</p>
          <div className="mt-4 flex items-center justify-between border-y border-[rgba(45,29,22,0.12)] py-4">
            <div>
              <h2 className="font-display text-[1.85rem] leading-none">Suitcase</h2>
              <p className="mt-2 text-[12px] uppercase tracking-[0.24em] text-[#8a5b24]">Guest Property Ledger</p>
            </div>
            <button
              type="button"
              className="rounded-full border border-[rgba(45,29,22,0.12)] px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-[#6f584b] transition hover:border-[#6f2430]/25 hover:text-[#6f2430]"
              onClick={onToggleInventory}
            >
              Close
            </button>
          </div>

          <div className="mt-6 grid grid-cols-3 gap-3">
            {INVENTORY_ITEMS.map((item) => (
              <article
                key={item.name}
                className="aspect-square rounded-[20px] border border-[rgba(45,29,22,0.12)] bg-[linear-gradient(180deg,rgba(243,234,223,0.98)_0%,rgba(233,216,192,0.92)_100%)] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.45)]"
              >
                <div className="flex h-full flex-col justify-between rounded-[16px] border border-[rgba(45,29,22,0.08)] px-3 py-2">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-[#8a5b24]">{item.detail}</p>
                  <p className="font-display text-3xl leading-none text-[#6f2430]">{item.mark}</p>
                  <p className="text-sm uppercase tracking-[0.18em] text-[#2d1d16]">{item.name}</p>
                </div>
              </article>
            ))}
          </div>
        </aside>
      ) : null}

      {isChatOpen ? (
        <aside className="absolute bottom-8 right-8 top-28 z-30 flex w-[25rem] flex-col rounded-[28px] border border-white/12 bg-[rgba(45,29,22,0.78)] p-6 text-parchment shadow-[0_24px_80px_rgba(0,0,0,0.38)] backdrop-blur-md">
          <div className="border-b border-white/10 pb-4">
            <p className="text-[11px] uppercase tracking-[0.34em] text-white/55">Hotel Exchange</p>
            <div className="mt-3 flex items-center justify-between">
              <div>
                <h2 className="font-display text-[1.85rem] leading-none">Chat Desk</h2>
                <p className="mt-2 text-[12px] uppercase tracking-[0.24em] text-[#b08a3e]">Private Concierge Wire</p>
              </div>
              <button
                type="button"
                className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-white/65 transition hover:border-[#b08a3e]/30 hover:text-parchment"
                onClick={onToggleChat}
              >
                Close
              </button>
            </div>
          </div>

          <div className="mt-6 flex-1 rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(243,234,223,0.1)_0%,rgba(243,234,223,0.04)_100%)] p-5">
            <p className="text-[11px] uppercase tracking-[0.28em] text-white/50">Front Office</p>
            <div className="mt-4 rounded-[20px] border border-[#b08a3e]/20 bg-[rgba(243,234,223,0.08)] p-4">
              <p className="text-sm leading-7 text-[#fcf6ee]">
                Welcome to Great Pannonia Hotel! You interact with the world via chat, so please tell me
                what you would like to do
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-[20px] border border-dashed border-white/12 bg-black/10 px-4 py-3 text-[12px] uppercase tracking-[0.18em] text-white/48">
            Chat input will arrive with the backend connection.
          </div>
        </aside>
      ) : null}

      <section className="relative z-10 flex min-h-screen items-center justify-center px-8 py-12">
        <div className="w-full max-w-5xl">
          <div className="mb-5 text-center text-parchment">
            <p className="text-[11px] uppercase tracking-[0.36em] text-white/60">Grand Pannonia Hotel</p>
            <h1 className="mt-4 font-display text-5xl leading-none drop-shadow-[0_14px_30px_rgba(0,0,0,0.42)]">
              The Lobby Awaits
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-white/78">
              Enter the marble hush of the hotel lobby and begin the first exchange of your investigation.
            </p>
          </div>

          <div className="rounded-[34px] border border-white/12 bg-[rgba(22,16,13,0.36)] p-4 shadow-[0_30px_90px_rgba(0,0,0,0.42)] backdrop-blur-sm">
            <div className="rounded-[28px] border border-[#b08a3e]/28 bg-[rgba(12,8,6,0.36)] p-4">
              <div className="relative overflow-hidden rounded-[24px] border border-white/8 bg-[rgba(18,13,10,0.9)]">
                {backgroundImageUrl ? (
                  <img
                    className="h-[68vh] min-h-[32rem] w-full object-cover object-center"
                    src={backgroundImageUrl}
                    alt="Grand hotel lobby with warm chandelier light, marble floors, and a sweeping staircase."
                  />
                ) : (
                  <div className="flex h-[68vh] min-h-[32rem] w-full items-center justify-center bg-[radial-gradient(circle_at_top,rgba(176,138,62,0.18),transparent_32%),linear-gradient(180deg,#281b15_0%,#120d0a_100%)]">
                    <p className="text-sm uppercase tracking-[0.28em] text-white/60">
                      {isLoadingImage ? "Preparing the lobby..." : "Lobby image unavailable"}
                    </p>
                  </div>
                )}

                <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(18,13,10,0.04)_0%,rgba(18,13,10,0.06)_58%,rgba(18,13,10,0.42)_100%)]" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <button
        type="button"
        className="absolute bottom-8 left-8 z-40 inline-flex items-center gap-3 rounded-full border border-[#b08a3e]/35 bg-[rgba(243,234,223,0.9)] px-5 py-4 text-walnut-ink shadow-[0_18px_42px_rgba(0,0,0,0.32)] backdrop-blur-md transition duration-200 hover:-translate-y-px hover:bg-[rgba(252,246,238,0.95)]"
        aria-pressed={isInventoryOpen}
        onClick={onToggleInventory}
      >
        <SuitcaseIcon />
        <span className="text-[12px] uppercase tracking-[0.28em]">Suitcase</span>
      </button>

      <button
        type="button"
        className="absolute bottom-8 right-8 z-40 inline-flex items-center gap-3 rounded-full border border-white/12 bg-[rgba(45,29,22,0.82)] px-5 py-4 text-parchment shadow-[0_18px_42px_rgba(0,0,0,0.32)] backdrop-blur-md transition duration-200 hover:-translate-y-px hover:bg-[rgba(60,39,31,0.88)]"
        aria-pressed={isChatOpen}
        onClick={onToggleChat}
      >
        <ChatIcon />
        <span className="text-[12px] uppercase tracking-[0.28em]">Chat Desk</span>
      </button>
    </main>
  );
}

export default GameShell;
