import React, { useCallback, useEffect, useRef, useState } from "react";

import AudioToggleButton from "./AudioToggleButton";
import GameShell from "./GameShell";
import OpeningAudioPlayer from "./OpeningAudioPlayer";
import StartScreen from "./StartScreen";

declare const __APP_BACKEND_HOST__: string;
declare const __APP_BACKEND_PORT__: string;

const HAS_STARTED_STORAGE_KEY = "grand-pannonia-has-started";
const CONSENT_ACCEPTED_STORAGE_KEY = "grand-pannonia-prototype-consent";
const SESSION_HEADER_NAME = "X-Grand-Pannonia-Session-Id";
const INITIAL_ASSISTANT_MESSAGE =
  "Welcome to the Grand Pannonia Hotel. Tell me what you would like to do, and I will keep it brief.";

type RoomStateResponse = {
  room_description?: string | null;
  room_name?: string;
  image_media_type: string;
  room_image_base64: string;
};

type SessionStateResponse = {
  current_room_name: string;
  session_id: string;
};

type InventoryItemResponse = {
  created_at: string;
  id: number;
  image_media_type: string;
  item_detail: string;
  item_image_base64: string;
  item_key: string;
  item_name: string;
  session_id: string;
};

type InventoryItem = {
  detail: string;
  id: number;
  imageSrc: string;
  itemKey: string;
  name: string;
};

type ChatMessage = {
  content: string;
  id: string;
  role: "assistant" | "user";
};

type ParsedSseEvent = {
  eventName: string;
  payload: Record<string, unknown>;
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

function createInitialMessages(): ChatMessage[] {
  return [{ id: "assistant-welcome", role: "assistant", content: INITIAL_ASSISTANT_MESSAGE }];
}

function parseSseEvent(rawEvent: string): ParsedSseEvent | null {
  const lines = rawEvent.split("\n");
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    eventName,
    payload: JSON.parse(dataLines.join("\n")) as Record<string, unknown>,
  };
}

function App() {
  const [hasStarted, setHasStarted] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.sessionStorage.getItem(HAS_STARTED_STORAGE_KEY) === "true";
  });
  const [hasConsented, setHasConsented] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.sessionStorage.getItem(CONSENT_ACCEPTED_STORAGE_KEY) === "true";
  });
  const [isAudioMuted, setIsAudioMuted] = useState(true);
  const [isStartNoticeOpen, setIsStartNoticeOpen] = useState(false);
  const [isIntroModalOpen, setIsIntroModalOpen] = useState(false);
  const [isInventoryOpen, setIsInventoryOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.sessionStorage.getItem(HAS_STARTED_STORAGE_KEY) === "true";
  });
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [currentRoomName, setCurrentRoomName] = useState("lobby");
  const [roomImageUrl, setRoomImageUrl] = useState<string | null>(null);
  const [isRoomImageLoading, setIsRoomImageLoading] = useState(false);
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() => createInitialMessages());
  const [chatDraft, setChatDraft] = useState("");
  const [chatError, setChatError] = useState<string | null>(null);
  const [isStreamingChat, setIsStreamingChat] = useState(false);
  const activeChatRequestRef = useRef<AbortController | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const backendBaseUrl = getBackendBaseUrl();
  const openingThemeUrl = `${backendBaseUrl}/audio/opening-theme`;
  const introAudioUrl = `${backendBaseUrl}/audio/intro`;
  const openingThemeVolume = isIntroModalOpen && !isAudioMuted ? 0.3 : 1;

  const syncSessionId = useCallback((response: Response, fallbackSessionId?: string | null): void => {
    const headerSessionId = response.headers.get(SESSION_HEADER_NAME)?.trim();
    const nextSessionId = headerSessionId || fallbackSessionId?.trim();
    if (nextSessionId) {
      sessionIdRef.current = nextSessionId;
    }
  }, []);

  const buildSessionHeaders = useCallback(
    (headers: Record<string, string> = {}): Record<string, string> => {
      if (sessionIdRef.current) {
        return { ...headers, [SESSION_HEADER_NAME]: sessionIdRef.current };
      }
      return headers;
    },
    [],
  );

  const ensureWelcomeMessage = useCallback(() => {
    setChatMessages((currentMessages) =>
      currentMessages.length > 0 ? currentMessages : createInitialMessages(),
    );
  }, []);

  const loadSessionState = useCallback(async (): Promise<string> => {
    const response = await fetch(`${backendBaseUrl}/session/state`, {
      credentials: "include",
      headers: buildSessionHeaders(),
    });
    if (!response.ok) {
      throw new Error(`Failed to load session state: ${response.status}`);
    }

    const payload = (await response.json()) as SessionStateResponse;
    syncSessionId(response, payload.session_id ?? null);
    const nextRoomName = payload.current_room_name || "lobby";
    setCurrentRoomName(nextRoomName);
    return nextRoomName;
  }, [backendBaseUrl, buildSessionHeaders, hasConsented, syncSessionId]);

  const loadInventory = useCallback(async (): Promise<void> => {
    const response = await fetch(`${backendBaseUrl}/inventory`, {
      credentials: "include",
      headers: buildSessionHeaders(),
    });
    if (!response.ok) {
      throw new Error(`Failed to load inventory: ${response.status}`);
    }

    syncSessionId(response);
    const payload = (await response.json()) as InventoryItemResponse[];
    setInventoryItems(
      payload.map((item) => ({
        id: item.id,
        itemKey: item.item_key,
        name: item.item_name,
        detail: item.item_detail,
        imageSrc: `data:${item.image_media_type};base64,${item.item_image_base64}`,
      })),
    );
  }, [backendBaseUrl, hasConsented]);

  const loadCurrentRoomImage = useCallback(
    async (roomName: string, signal: AbortSignal): Promise<void> => {
      setIsRoomImageLoading(true);
      try {
        const response = await fetch(`${backendBaseUrl}/rooms/${encodeURIComponent(roomName)}/latest`, {
          credentials: "include",
          headers: buildSessionHeaders(),
          signal,
        });
        if (!response.ok) {
          throw new Error(`Failed to load room image: ${response.status}`);
        }

        syncSessionId(response);
        const roomState = (await response.json()) as RoomStateResponse;
        setRoomImageUrl(`data:${roomState.image_media_type};base64,${roomState.room_image_base64}`);
      } finally {
        if (!signal.aborted) {
          setIsRoomImageLoading(false);
        }
      }
    },
    [backendBaseUrl, buildSessionHeaders, syncSessionId],
  );

  async function handleResetExperience(): Promise<void> {
    setIsResetting(true);
    setResetError(null);

    try {
      const response = await fetch(`${backendBaseUrl}/session/reset`, {
        method: "POST",
        credentials: "include",
          headers: buildSessionHeaders(),
      });

      if (!response.ok) {
        let errorMessage = `Failed to reset progress: ${response.status}`;
        try {
          const payload = (await response.json()) as { error?: string };
          if (typeof payload.error === "string" && payload.error) {
            errorMessage = payload.error;
          }
        } catch {
          // Keep the status-based fallback when the error body is unavailable.
        }
        throw new Error(errorMessage);
      }

      syncSessionId(response);
      setHasStarted(false);
      setIsInventoryOpen(false);
      setIsChatOpen(false);
      setIsResetModalOpen(false);
      setIsStartNoticeOpen(false);
      setIsIntroModalOpen(false);
      setChatDraft("");
      setChatError(null);
      setChatMessages(createInitialMessages());
      setInventoryItems([]);
      setRoomImageUrl(null);
      setCurrentRoomName("lobby");
      const nextRoomName = await loadSessionState();
      await loadInventory();
      const controller = new AbortController();
      await loadCurrentRoomImage(nextRoomName, controller.signal);
    } catch (error) {
      console.error("Could not reset the current session.", error);
      setResetError(error instanceof Error ? error.message : "Could not reset the current session.");
    } finally {
      setIsResetting(false);
    }
  }

  useEffect(() => {
    window.sessionStorage.setItem(HAS_STARTED_STORAGE_KEY, String(hasStarted));
  }, [hasStarted]);

  useEffect(() => {
    window.sessionStorage.setItem(CONSENT_ACCEPTED_STORAGE_KEY, String(hasConsented));
  }, [hasConsented]);

  useEffect(() => {
    void (async () => {
      try {
        const nextRoomName = await loadSessionState();
      } catch (error) {
        console.error("Could not bootstrap the current session.", error);
      }
    })();
  }, [loadSessionState]);

  useEffect(() => {
    const controller = new AbortController();
    void loadCurrentRoomImage(currentRoomName, controller.signal).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        console.error(`Could not load the image for ${currentRoomName}.`, error);
      }
    });

    return () => {
      controller.abort();
    };
  }, [currentRoomName, loadCurrentRoomImage]);

  useEffect(() => {
    if (!hasStarted || !hasConsented) {
      setInventoryItems([]);
      return;
    }

    void (async () => {
      try {
        const nextRoomName = await loadSessionState();
        await loadInventory();
        const refreshController = new AbortController();
        await loadCurrentRoomImage(nextRoomName, refreshController.signal);
      } catch (error) {
        console.error("Could not load the entered session state.", error);
      }
    })();
  }, [hasConsented, hasStarted, loadCurrentRoomImage, loadInventory, loadSessionState]);

  useEffect(() => {
    return () => {
      activeChatRequestRef.current?.abort();
    };
  }, []);

  const handleSendChatMessage = useCallback(
    async (message: string): Promise<void> => {
      const trimmedMessage = message.trim();
      if (!trimmedMessage || isStreamingChat) {
        return;
      }

      const userMessageId = `user-${Date.now()}`;
      const assistantMessageId = `assistant-${Date.now()}`;
      setChatDraft("");
      setChatError(null);
      setIsStreamingChat(true);
      setChatMessages((currentMessages) => [
        ...currentMessages,
        { id: userMessageId, role: "user", content: trimmedMessage },
        { id: assistantMessageId, role: "assistant", content: "" },
      ]);

      const controller = new AbortController();
      activeChatRequestRef.current = controller;

      try {
        const response = await fetch(`${backendBaseUrl}/chat/stream`, {
          method: "POST",
          credentials: "include",
          headers: buildSessionHeaders({
            Accept: "text/event-stream",
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({ message: trimmedMessage }),
          signal: controller.signal,
        });

        if (!response.ok) {
          let errorMessage = `Failed to stream chat response: ${response.status}`;
          try {
            const payload = (await response.json()) as { error?: string };
            if (typeof payload.error === "string" && payload.error) {
              errorMessage = payload.error;
            }
          } catch {
            // Keep the status fallback when the error body is unavailable.
          }
          throw new Error(errorMessage);
        }

        syncSessionId(response);
        if (!response.body) {
          throw new Error("The chat stream did not return a readable response body.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          let boundaryIndex = buffer.indexOf("\n\n");
          while (boundaryIndex !== -1) {
            const rawEvent = buffer.slice(0, boundaryIndex);
            buffer = buffer.slice(boundaryIndex + 2);
            boundaryIndex = buffer.indexOf("\n\n");

            const parsedEvent = parseSseEvent(rawEvent);
            if (!parsedEvent) {
              continue;
            }

            if (parsedEvent.eventName === "delta" && typeof parsedEvent.payload.content === "string") {
              setChatMessages((currentMessages) =>
                currentMessages.map((chatMessage) =>
                  chatMessage.id === assistantMessageId
                    ? { ...chatMessage, content: chatMessage.content + parsedEvent.payload.content }
                    : chatMessage,
                ),
              );
            }

            if (parsedEvent.eventName === "complete" && typeof parsedEvent.payload.content === "string") {
              setChatMessages((currentMessages) =>
                currentMessages.map((chatMessage) =>
                  chatMessage.id === assistantMessageId && chatMessage.content.length === 0
                    ? { ...chatMessage, content: parsedEvent.payload.content }
                    : chatMessage,
                ),
              );
            }

            if (parsedEvent.eventName === "error") {
              const streamMessage =
                typeof parsedEvent.payload.message === "string"
                  ? parsedEvent.payload.message
                  : "The concierge could not complete that request.";
              throw new Error(streamMessage);
            }
          }
        }

        const nextRoomName = await loadSessionState();
        await loadInventory();
        const refreshController = new AbortController();
        await loadCurrentRoomImage(nextRoomName, refreshController.signal);
      } catch (error) {
        console.error("Could not complete the chat request.", error);
        const fallbackMessage =
          error instanceof Error ? error.message : "The concierge could not complete that request.";
        setChatError(fallbackMessage);
        setChatMessages((currentMessages) =>
          currentMessages.map((chatMessage) =>
            chatMessage.id === assistantMessageId && chatMessage.content.length === 0
              ? { ...chatMessage, content: "I could not complete that just now." }
              : chatMessage,
          ),
        );
      } finally {
        setIsStreamingChat(false);
        if (activeChatRequestRef.current === controller) {
          activeChatRequestRef.current = null;
        }
      }
    },
    [backendBaseUrl, buildSessionHeaders, isStreamingChat, loadCurrentRoomImage, loadInventory, loadSessionState, syncSessionId],
  );

  return (
    <>
      <OpeningAudioPlayer audioUrl={openingThemeUrl} isMuted={isAudioMuted} volume={openingThemeVolume} />
      <AudioToggleButton isMuted={isAudioMuted} onToggle={() => setIsAudioMuted((currentValue) => !currentValue)} />

      {hasStarted ? (
        <GameShell
          backgroundImageUrl={roomImageUrl}
          roomName={currentRoomName}
          inventoryItems={inventoryItems}
          chatMessages={chatMessages}
          chatDraft={chatDraft}
          chatError={chatError}
          isStreamingChat={isStreamingChat}
          isLoadingImage={isRoomImageLoading}
          isInventoryOpen={isInventoryOpen}
          isChatOpen={isChatOpen}
          isResetModalOpen={isResetModalOpen}
          isResetting={isResetting}
          resetError={resetError}
          onChatDraftChange={setChatDraft}
          onSendChatMessage={(message) => {
            void handleSendChatMessage(message);
          }}
          onToggleInventory={() => setIsInventoryOpen((currentValue) => !currentValue)}
          onToggleChat={() => setIsChatOpen((currentValue) => !currentValue)}
          onOpenResetModal={() => {
            setResetError(null);
            setIsResetModalOpen(true);
          }}
          onCloseResetModal={() => {
            if (isResetting) {
              return;
            }
            setResetError(null);
            setIsResetModalOpen(false);
          }}
          onConfirmReset={() => {
            void handleResetExperience();
          }}
        />
      ) : (
        <StartScreen
          backgroundImageUrl={roomImageUrl}
          isLoadingImage={isRoomImageLoading}
          isNoticeOpen={isStartNoticeOpen}
          isIntroOpen={isIntroModalOpen}
          hasConsented={hasConsented}
          introAudioUrl={introAudioUrl}
          isAudioMuted={isAudioMuted}
          onConsentChange={setHasConsented}
          onCloseNotice={() => {
            setIsStartNoticeOpen(false);
          }}
          onCloseIntro={() => {
            setIsIntroModalOpen(false);
            setHasStarted(true);
            setIsChatOpen(true);
          }}
          onConfirmStart={() => {
            ensureWelcomeMessage();
            setIsStartNoticeOpen(false);
            setIsIntroModalOpen(true);
          }}
          onStart={() => {
            if (hasConsented) {
              ensureWelcomeMessage();
              setIsIntroModalOpen(true);
              return;
            }
            setIsStartNoticeOpen(true);
          }}
        />
      )}
    </>
  );
}

export default App;
