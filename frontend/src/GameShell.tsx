import React from "react";

import bookImage from "./assets/inventory/book.png";
import cashImage from "./assets/inventory/cash.png";
import contractImage from "./assets/inventory/contract.png";
import penImage from "./assets/inventory/pen.png";
import scarfImage from "./assets/inventory/scarf.png";
import teddyImage from "./assets/inventory/teddy.png";
import watchImage from "./assets/inventory/watch.png";

type GameShellProps = {
  backgroundImageUrl: string | null;
  isLoadingImage: boolean;
  isInventoryOpen: boolean;
  isChatOpen: boolean;
  isResetModalOpen: boolean;
  isResetting: boolean;
  resetError: string | null;
  onToggleInventory: () => void;
  onToggleChat: () => void;
  onOpenResetModal: () => void;
  onCloseResetModal: () => void;
  onConfirmReset: () => void;
};

type MockInventoryItem = {
  detail: string;
  imageSrc: string;
  name: string;
};

const INVENTORY_ITEMS: MockInventoryItem[] = [
  { name: "Pen", imageSrc: penImage, detail: "Reception Desk" },
  { name: "Book", imageSrc: bookImage, detail: "Guest Library" },
  { name: "Contract", imageSrc: contractImage, detail: "Signed Copy" },
  { name: "Cash", imageSrc: cashImage, detail: "Tucked Away" },
  { name: "Teddy", imageSrc: teddyImage, detail: "Nursery Find" },
  { name: "Watch", imageSrc: watchImage, detail: "Pocket Piece" },
  { name: "Scarf", imageSrc: scarfImage, detail: "Velvet Clue" },
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

function ResetIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
      <path
        d="M6.75 8.75H3.75V5.75"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
      <path
        d="M4 8.25C5.49 6.04 8.02 4.75 10.75 4.75C15.03 4.75 18.5 8.22 18.5 12.5C18.5 16.78 15.03 20.25 10.75 20.25C7.48 20.25 4.68 18.22 3.56 15.34"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

type InventoryIconProps = {
  kind: MockInventoryItem["icon"];
};

function GameShell({
  backgroundImageUrl,
  isLoadingImage,
  isInventoryOpen,
  isChatOpen,
  isResetModalOpen,
  isResetting,
  resetError,
  onToggleInventory,
  onToggleChat,
  onOpenResetModal,
  onCloseResetModal,
  onConfirmReset,
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

      {isResetModalOpen ? (
        <div className="absolute inset-0 z-[60] flex items-center justify-center bg-[rgba(18,13,10,0.68)] px-6 backdrop-blur-sm">
          <section className="w-full max-w-xl rounded-[28px] border border-[#b08a3e]/28 bg-[linear-gradient(180deg,rgba(252,246,238,0.97)_0%,rgba(233,216,192,0.96)_100%)] p-7 text-walnut-ink shadow-[0_30px_90px_rgba(0,0,0,0.42)]">
            <p className="text-[11px] uppercase tracking-[0.34em] text-[#8a5b24]">Private Notice</p>
            <h2 className="mt-4 font-display text-[2rem] leading-none text-[#2d1d16]">Reset your stay?</h2>
            <p className="mt-4 text-sm leading-7 text-[#4a352c]">
              This will delete the current session&apos;s progress, close the active overlays, and return you to
              the start screen.
            </p>
            {resetError ? (
              <p className="mt-4 rounded-[18px] border border-[#6f2430]/18 bg-[rgba(111,36,48,0.08)] px-4 py-3 text-sm leading-6 text-[#6f2430]">
                {resetError}
              </p>
            ) : null}
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                className="rounded-full border border-[rgba(45,29,22,0.14)] bg-transparent px-5 py-3 text-[12px] uppercase tracking-[0.24em] text-[#6f584b] transition hover:border-[#2d1d16]/20 hover:text-[#2d1d16] disabled:cursor-not-allowed disabled:opacity-60"
                onClick={onCloseResetModal}
                disabled={isResetting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-full border border-[#6f2430]/18 bg-[linear-gradient(180deg,rgba(111,36,48,0.96)_0%,rgba(79,23,34,0.98)_100%)] px-5 py-3 text-[12px] uppercase tracking-[0.24em] text-[#fcf6ee] shadow-[0_18px_40px_rgba(0,0,0,0.22)] transition hover:-translate-y-px hover:shadow-[0_22px_42px_rgba(0,0,0,0.26)] disabled:cursor-not-allowed disabled:opacity-60"
                onClick={onConfirmReset}
                disabled={isResetting}
              >
                {isResetting ? "Resetting..." : "Reset Progress"}
              </button>
            </div>
          </section>
        </div>
      ) : null}

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
                className="group relative aspect-square rounded-[20px] border border-[rgba(45,29,22,0.12)] bg-[linear-gradient(180deg,rgba(243,234,223,0.98)_0%,rgba(233,216,192,0.92)_100%)] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.45)]"
              >
                <div className="pointer-events-none absolute -top-4 left-1/2 z-20 w-[13rem] max-w-[13rem] -translate-x-1/2 -translate-y-full rounded-[22px] border border-[rgba(45,29,22,0.12)] bg-[linear-gradient(180deg,rgba(252,246,238,0.98)_0%,rgba(233,216,192,0.95)_100%)] p-3 opacity-0 shadow-[0_20px_40px_rgba(0,0,0,0.22)] transition duration-200 group-hover:opacity-100">
                  <div className="overflow-hidden rounded-[16px] border border-[rgba(45,29,22,0.08)]">
                    <img className="h-32 w-full object-cover object-center" src={item.imageSrc} alt="" aria-hidden="true" />
                  </div>
                  <div className="mt-3 text-center">
                    <p className="text-[10px] uppercase tracking-[0.24em] text-[#8a5b24]">{item.detail}</p>
                    <p className="mt-2 text-sm uppercase tracking-[0.18em] text-[#2d1d16]">{item.name}</p>
                  </div>
                </div>
                <div className="relative h-full overflow-hidden rounded-[16px] border border-[rgba(45,29,22,0.08)] bg-[rgba(252,246,238,0.42)]">
                  <img
                    className="h-full w-full object-cover object-center transition duration-300 group-hover:scale-[1.03]"
                    src={item.imageSrc}
                    alt={item.name}
                  />
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

      <section className="relative z-10 min-h-screen px-8 py-8">
        {backgroundImageUrl ? (
          <img
            className="h-[calc(100vh-4rem)] min-h-[36rem] w-full object-cover object-center"
            src={backgroundImageUrl}
            alt="Grand hotel lobby with warm chandelier light, marble floors, and a sweeping staircase."
          />
        ) : (
          <div className="flex h-[calc(100vh-4rem)] min-h-[36rem] w-full items-center justify-center bg-[radial-gradient(circle_at_top,rgba(176,138,62,0.18),transparent_32%),linear-gradient(180deg,#281b15_0%,#120d0a_100%)]">
            <p className="text-sm uppercase tracking-[0.28em] text-white/60">
              {isLoadingImage ? "Preparing the lobby..." : "Lobby image unavailable"}
            </p>
          </div>
        )}
      </section>

      <button
        type="button"
        className="absolute left-8 top-8 z-40 inline-flex items-center gap-3 rounded-full border border-[#b08a3e]/35 bg-[rgba(243,234,223,0.9)] px-5 py-4 text-walnut-ink shadow-[0_18px_42px_rgba(0,0,0,0.32)] backdrop-blur-md transition duration-200 hover:-translate-y-px hover:bg-[rgba(252,246,238,0.95)]"
        onClick={onOpenResetModal}
      >
        <ResetIcon />
        <span className="text-[12px] uppercase tracking-[0.28em]">Reset</span>
      </button>

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
