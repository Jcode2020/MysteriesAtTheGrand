import React, { useEffect, useRef } from "react";

type GameShellProps = {
  backgroundImageUrl: string | null;
  isLoadingImage: boolean;
  roomName: string;
  inventoryItems: InventoryItem[];
  chatMessages: ChatMessage[];
  chatDraft: string;
  chatError: string | null;
  isStreamingChat: boolean;
  isInventoryOpen: boolean;
  isChatOpen: boolean;
  isResetModalOpen: boolean;
  isResetting: boolean;
  resetError: string | null;
  onChatDraftChange: (nextDraft: string) => void;
  onSendChatMessage: (message: string) => void;
  onToggleInventory: () => void;
  onToggleChat: () => void;
  onOpenResetModal: () => void;
  onCloseResetModal: () => void;
  onConfirmReset: () => void;
};

type InventoryItem = {
  id: number;
  detail: string;
  imageSrc: string;
  itemKey: string;
  name: string;
};

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

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

function InteractionIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
      <path
        d="M12 3.75L13.37 7.4L17 8.77L13.37 10.14L12 13.79L10.63 10.14L7 8.77L10.63 7.4L12 3.75Z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
      <path
        d="M18.25 12.25L19.02 14.23L21 15L19.02 15.77L18.25 17.75L17.48 15.77L15.5 15L17.48 14.23L18.25 12.25Z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
      <path
        d="M6.25 13.25L6.93 15.07L8.75 15.75L6.93 16.43L6.25 18.25L5.57 16.43L3.75 15.75L5.57 15.07L6.25 13.25Z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
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

function formatRoomName(roomName: string): string {
  return roomName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function GameShell({
  backgroundImageUrl,
  isLoadingImage,
  roomName,
  inventoryItems,
  chatMessages,
  chatDraft,
  chatError,
  isStreamingChat,
  isInventoryOpen,
  isChatOpen,
  isResetModalOpen,
  isResetting,
  resetError,
  onChatDraftChange,
  onSendChatMessage,
  onToggleInventory,
  onToggleChat,
  onOpenResetModal,
  onCloseResetModal,
  onConfirmReset,
}: GameShellProps) {
  const formattedRoomName = formatRoomName(roomName);
  const lastAssistantMessage = [...chatMessages].reverse().find((message) => message.role === "assistant");
  const chatScrollContainerRef = useRef<HTMLDivElement | null>(null);
  const shouldStickToBottomRef = useRef(true);

  useEffect(() => {
    if (!isChatOpen || !chatScrollContainerRef.current) {
      return;
    }

    const chatScrollContainer = chatScrollContainerRef.current;
    const distanceFromBottom =
      chatScrollContainer.scrollHeight - chatScrollContainer.clientHeight - chatScrollContainer.scrollTop;
    if (shouldStickToBottomRef.current || distanceFromBottom < 48) {
      chatScrollContainer.scrollTop = chatScrollContainer.scrollHeight;
      shouldStickToBottomRef.current = true;
    }
  }, [chatMessages, isChatOpen, isStreamingChat]);

  useEffect(() => {
    if (!isChatOpen || !chatScrollContainerRef.current) {
      return;
    }

    const chatScrollContainer = chatScrollContainerRef.current;
    chatScrollContainer.scrollTop = chatScrollContainer.scrollHeight;
    shouldStickToBottomRef.current = true;
  }, [isChatOpen]);

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
        <aside className="absolute bottom-28 left-8 z-30 flex max-h-[min(68vh,34rem)] min-h-0 w-[min(22rem,calc(100vw-4rem))] flex-col rounded-[28px] border border-[#b08a3e]/35 bg-[rgba(252,246,238,0.92)] p-6 text-walnut-ink shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur-md">
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

          <div className="mt-6 grid flex-1 auto-rows-max grid-cols-3 gap-3 overflow-y-auto pr-1">
            {inventoryItems.length > 0 ? (
              inventoryItems.map((item) => (
                <article
                  key={item.id}
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
              ))
            ) : (
              <div className="col-span-3 rounded-[22px] border border-dashed border-[rgba(45,29,22,0.14)] bg-[rgba(252,246,238,0.5)] px-4 py-8 text-center">
                <p className="text-[11px] uppercase tracking-[0.24em] text-[#8a5b24]">Suitcase Empty</p>
                <p className="mt-3 text-sm leading-7 text-[#4a352c]">No travel effects are currently stored in this session.</p>
              </div>
            )}
          </div>
        </aside>
      ) : null}

      {isChatOpen ? (
        <aside
          className="absolute bottom-26 right-8 z-30 flex max-h-[min(78vh,42rem)] min-h-0 w-[min(31rem,calc(100vw-3rem))] flex-col rounded-[28px] border border-white/12 bg-[rgba(45,29,22,0.78)] p-4 text-parchment shadow-[0_24px_80px_rgba(0,0,0,0.38)] backdrop-blur-md"
        >
          <div className="border-b border-white/10 pb-3">
            <p className="text-[11px] uppercase tracking-[0.34em] text-white/55">World Interaction</p>
            <div className="mt-2 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-display text-[1.55rem] leading-none">Interaction</h2>
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

          <div className="mt-3 flex min-h-0 flex-1 overflow-hidden rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(243,234,223,0.1)_0%,rgba(243,234,223,0.04)_100%)] p-3">
            <div
              ref={chatScrollContainerRef}
              className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto overscroll-contain pr-2"
              onScroll={(event) => {
                const chatScrollContainer = event.currentTarget;
                const distanceFromBottom =
                  chatScrollContainer.scrollHeight - chatScrollContainer.clientHeight - chatScrollContainer.scrollTop;
                shouldStickToBottomRef.current = distanceFromBottom < 48;
              }}
            >
              {chatMessages.map((message) => (
                <article
                  key={message.id}
                  className={
                    message.role === "user"
                      ? "ml-8 rounded-[18px] border border-[#b08a3e]/24 bg-[rgba(176,138,62,0.14)] px-3 py-2.5 text-sm leading-6 text-[#fcf6ee]"
                      : "mr-8 rounded-[18px] border border-white/10 bg-[rgba(243,234,223,0.08)] px-3 py-2.5 text-sm leading-6 text-[#fcf6ee]"
                  }
                >
                  <p className="text-[9px] uppercase tracking-[0.2em] text-white/45">
                    {message.role === "user" ? "Guest" : "Grand Pannonia Hotel"}
                  </p>
                  <p className="mt-1.5 whitespace-pre-wrap">
                    {message.content || (isStreamingChat && lastAssistantMessage?.id === message.id ? <span className="typing-dots" aria-label="Grand Pannonia Hotel is responding"><span>.</span><span>.</span><span>.</span></span> : "")}
                  </p>
                </article>
              ))}
            </div>
          </div>

          {chatError ? (
            <div className="mt-3 rounded-[18px] border border-[#6f2430]/28 bg-[rgba(111,36,48,0.12)] px-3 py-2.5 text-sm leading-6 text-[#f7d6da]">
              {chatError}
            </div>
          ) : null}

          <form
            className="mt-3 rounded-[20px] border border-white/10 bg-black/10 p-2.5"
            onSubmit={(event) => {
              event.preventDefault();
              onSendChatMessage(chatDraft);
            }}
          >
            <label className="sr-only" htmlFor="chat-composer">
              Message Grand Pannonia Hotel
            </label>
            <textarea
              id="chat-composer"
              className="min-h-[3.5rem] max-h-28 w-full resize-none rounded-[16px] border border-white/10 bg-[rgba(252,246,238,0.06)] px-3 py-2.5 text-sm leading-5 text-[#fcf6ee] outline-none placeholder:text-white/35 focus:border-[#b08a3e]/45"
              placeholder="Tell me how you want to interact with the world"
              value={chatDraft}
              onChange={(event) => onChatDraftChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key !== "Enter") {
                  return;
                }
                if (!event.shiftKey) {
                  event.preventDefault();
                  onSendChatMessage(chatDraft);
                }
              }}
              disabled={isStreamingChat}
            />
            <div className="mt-2 flex items-center justify-between gap-3">
              <p className="text-[10px] uppercase tracking-[0.18em] text-white/42">{isStreamingChat ? "Grand Pannonia Hotel is responding..." : ""}</p>
              <button
                type="submit"
                className="rounded-full border border-[#b08a3e]/24 bg-[linear-gradient(180deg,rgba(111,36,48,0.96)_0%,rgba(79,23,34,0.98)_100%)] px-4 py-2 text-[10px] uppercase tracking-[0.22em] text-[#fcf6ee] transition hover:-translate-y-px disabled:cursor-not-allowed disabled:opacity-55"
                disabled={isStreamingChat || chatDraft.trim().length === 0}
              >
                Send
              </button>
            </div>
          </form>
        </aside>
      ) : null}

      <section className="relative z-10 min-h-screen px-8 py-8">
        {backgroundImageUrl ? (
          <img
            className="h-[calc(100vh-4rem)] min-h-[36rem] w-full object-cover object-center"
            src={backgroundImageUrl}
            alt={`Current view of the ${formattedRoomName}.`}
          />
        ) : (
          <div className="flex h-[calc(100vh-4rem)] min-h-[36rem] w-full items-center justify-center bg-[radial-gradient(circle_at_top,rgba(176,138,62,0.18),transparent_32%),linear-gradient(180deg,#281b15_0%,#120d0a_100%)]">
            <p className="text-sm uppercase tracking-[0.28em] text-white/60">
              {isLoadingImage ? `Preparing ${formattedRoomName}...` : `${formattedRoomName} image unavailable`}
            </p>
          </div>
        )}
      </section>

      <div className="pointer-events-none absolute left-1/2 top-8 z-30 -translate-x-1/2 rounded-full border border-[#b08a3e]/28 bg-[rgba(28,18,14,0.66)] px-5 py-3 text-center shadow-[0_18px_42px_rgba(0,0,0,0.24)] backdrop-blur-md">
        <p className="text-[11px] uppercase tracking-[0.26em] text-[#e9d8c0]">Current Room</p>
        <p className="mt-2 font-display text-2xl leading-none text-[#fcf6ee]">{formattedRoomName}</p>
      </div>

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
        <InteractionIcon />
        <span className="text-[12px] uppercase tracking-[0.28em]">Interaction</span>
      </button>
    </main>
  );
}

export default GameShell;
