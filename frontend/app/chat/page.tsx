"use client";

import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import { useSession, getSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { BackgroundBeams } from "../../components/ui/background-beams";
import { PlaceholdersAndVanishInput } from "../../components/ui/placeholders-and-vanish-input";
import { FlipWords } from "../../components/ui/flip-words";
// CORRECT Anime.js v4 named imports
import { animate, stagger } from "animejs";
import { cva, type VariantProps } from "class-variance-authority";
import { twMerge } from "tailwind-merge";
import { clsx } from "clsx";
import MessageItem from "./MessageItem";
import { LoaderThree } from "../../components/ui/loader";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { ChatSidebar } from "../../components/chat-sidebar";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import LunaAvatar from "/luna-avatar.jpg";

export function LoaderThreeDemo() {
  return <LoaderThree />;
}

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-full text-sm font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none hover:scale-105 active:scale-95",
  {
    variants: {
      variant: {
        default:
          "bg-blue-500 text-white shadow-lg shadow-blue-500/30 hover:bg-blue-500/90",
        destructive:
          "bg-gradient-to-r from-red-500 to-orange-500 text-white shadow-lg shadow-red-500/40 hover:opacity-90",
      },
      size: {
        default: "h-12 px-6",
        icon: "h-7 w-7",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={twMerge(clsx(buttonVariants({ variant, size, className })))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

// --- INTERFACES ---
interface ToolEvent {
  tool: string;
  args: { [key: string]: any };
  duration_ms: number;
  success: boolean;
  error: string | null;
  output_excerpt: string;
}

interface Message {
  id: number;
  content: string;
  role: "user" | "assistant";
  timestamp: string;
  tool_events?: ToolEvent[];
}

interface UserSession {
  session_id: string;
  last_updated: string;
  message_count: number;
}

export default function ChatPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // --- ALL STATE VARIABLES ---
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [sessionId, setSessionId] = useState<string>("");
  const [userSessions, setUserSessions] = useState<UserSession[]>([]);
  const [apiStatus, setApiStatus] = useState<
    "connecting" | "connected" | "error"
  >("connecting");
  const [currentGeneratingId, setCurrentGeneratingId] = useState<number | null>(
    null,
  );
  const [typingText, setTypingText] = useState<{ [key: number]: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [typingEffectEnabled, setTypingEffectEnabled] = useState(true);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const [newMessagesCount, setNewMessagesCount] = useState(0);
  const [hasAnimatedIn, setHasAnimatedIn] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false); // Add this state

  const flipWords = ["helpful", "creative", "intelligent", "powerful"];

  // --- ALL REFS ---
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const chatLayoutRef = useRef<HTMLDivElement>(null);
  const welcomeHeaderRef = useRef<HTMLDivElement>(null);
  const chatWrapperRef = useRef<HTMLDivElement>(null);
  const lastMessageCountRef = useRef<number>(0);
  const typingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const placeholders = useMemo(
    () => [
      "Ask me anything...",
      "How can I help you today?",
      "What would you like to know?",
    ],
    [],
  );

  const resetChatUI = useCallback(() => {
    setMessages([]);
    setHasAnimatedIn(false);
  }, []);

  // --- SESSION MANAGEMENT FUNCTIONS ---
  const fetchSessionHistory = useCallback(
    async (sessionId: string, email: string) => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/session/${sessionId}/history?email=${email}`,
        );
        if (!response.ok) throw new Error("Failed to fetch session history");
        const data = await response.json();
        const formattedMessages: Message[] = data.messages.map(
          (msg: any, index: number) => ({
            id: Date.now() + index,
            content: msg.content,
            role: msg.role === "assistant" ? "assistant" : "user",
            timestamp: msg.timestamp || new Date().toISOString(),
          }),
        );

        setSessionId(sessionId);
        setMessages(formattedMessages);

        if (formattedMessages.length > 0) {
          setHasAnimatedIn(true);
        } else {
          resetChatUI();
        }
      } catch (error) {
        console.error(error);
        toast.error("Could not load session history.");
      }
    },
    [resetChatUI],
  );

  const createNewSession = useCallback(
    async (email: string) => {
      try {
        const response = await fetch("http://localhost:8000/api/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });
        if (!response.ok) throw new Error("Failed to create new session");
        const data = await response.json();
        setSessionId(data.session_id);
        resetChatUI();
        toast.success("New chat created!");
        return data.session_id;
      } catch (error) {
        console.error(error);
        toast.error("Could not create a new chat.");
        return null;
      }
    },
    [resetChatUI],
  );

  // --- MAIN INITIALIZATION HOOK ---
  useEffect(() => {
    // Prevent re-initialization if already initialized
    if (isInitialized) return;

    if (status !== "authenticated" || !session?.user?.email) {
      if (status === "unauthenticated") router.push("/login");
      return;
    }

    const initUserAndSessions = async () => {
      const email = session.user!.email!;
      setIsPageLoading(true);
      setApiStatus("connecting");
      try {
        await fetch("http://localhost:8000/health");
        setApiStatus("connected");
        const sessionsResponse = await fetch(
          `http://localhost:8000/api/user/${email}/sessions`,
        );
        if (sessionsResponse.status === 404) {
          await createNewSession(email);
          setUserSessions([]);
        } else if (!sessionsResponse.ok) {
          throw new Error(
            `Failed to fetch sessions. Server responded with ${sessionsResponse.status}`,
          );
        } else {
          const sessionsData = await sessionsResponse.json();
          setUserSessions(sessionsData.sessions);
          if (sessionsData.sessions && sessionsData.sessions.length > 0) {
            await fetchSessionHistory(
              sessionsData.sessions[0].session_id,
              email,
            );
          } else {
            await createNewSession(email);
          }
        }
        setIsInitialized(true); // Mark as initialized
      } catch (error) {
        console.error("Initialization failed:", error);
        setApiStatus("error");
        toast.error(
          (error as Error).message || "Failed to initialize chat session.",
        );
      } finally {
        setIsPageLoading(false);
      }
    };

    initUserAndSessions();
  }, [
    status,
    session,
    router,
    fetchSessionHistory,
    createNewSession,
    isInitialized,
  ]);

  // --- HANDLERS TO PASS TO SIDEBAR ---
  const handleCreateNewSession = async () => {
    if (!session?.user?.email) return;
    const newSessionId = await createNewSession(session.user.email);
    if (newSessionId) {
      const sessionsResponse = await fetch(
        `http://localhost:8000/api/user/${session.user.email}/sessions`,
      );
      if (sessionsResponse.ok) {
        const sessionsData = await sessionsResponse.json();
        setUserSessions(sessionsData.sessions);
      }
    }
  };

  const handleSelectSession = async (selectedSessionId: string) => {
    if (!session?.user?.email || selectedSessionId === sessionId) return;
    setIsPageLoading(true);
    await fetchSessionHistory(selectedSessionId, session.user.email);
    setIsPageLoading(false);
  };

  // --- MODIFIED SESSION REFRESH HOOK ---
  useEffect(() => {
    // Only set up session refresh if already initialized
    if (!isInitialized) return;

    const interval = setInterval(
      async () => {
        if (status === "authenticated") {
          // Silently refresh session without triggering re-initialization
          await getSession();
        }
      },
      5 * 60 * 1000,
    );
    return () => clearInterval(interval);
  }, [status, isInitialized]); // Add isInitialized dependency

  const smoothScrollToBottom = useCallback(() => {
    if (!chatContainerRef.current) return;
    requestAnimationFrame(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTo({
          top: chatContainerRef.current.scrollHeight,
          behavior: "smooth",
        });
      }
    });
  }, []);

  useEffect(() => {
    smoothScrollToBottom();
  }, [messages, typingText, smoothScrollToBottom]);
  useEffect(() => {
    if (currentGeneratingId !== null) {
      smoothScrollToBottom();
    }
  }, [typingText, currentGeneratingId, smoothScrollToBottom]);
  useEffect(() => {
    const chatContainer = chatContainerRef.current;
    if (!chatContainer) return;
    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = chatContainer;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
      setShowScrollToBottom(!isAtBottom);
      if (isAtBottom) {
        setNewMessagesCount(0);
      }
    };
    chatContainer.addEventListener("scroll", handleScroll);
    return () => chatContainer.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const newMessagesCount = messages.length - lastMessageCountRef.current;
    if (newMessagesCount > 0) {
      const newElements = Array.from(
        document.querySelectorAll("[data-message-id]"),
      ).slice(-newMessagesCount);
      animate(newElements, {
        opacity: [0, 1],
        translateY: [25, 0],
        duration: 400,
        delay: stagger(100),
        easing: "easeOutCubic",
      });
      lastMessageCountRef.current = messages.length;
    }
  }, [messages]);

  // --- MODIFIED ANIMATION HOOK ---
  useEffect(() => {
    if (messages.length > 0 && !hasAnimatedIn && chatLayoutRef.current) {
      if (welcomeHeaderRef.current) {
        animate(welcomeHeaderRef.current, {
          opacity: 0,
          duration: 400,
          easing: "easeOutCubic",
        });
      }
      if (chatLayoutRef.current) {
        animate(chatLayoutRef.current, {
          justifyContent: ["center", "flex-end"],
          duration: 200,
          easing: "easeInOutSine",
        });
      }
      if (chatWrapperRef.current) {
        animate(chatWrapperRef.current, {
          maxHeight: ["0vh", "100vh"],
          opacity: [0, 1],
          duration: 500,
          easing: "easeInOutSine",
        });
      }
      setHasAnimatedIn(true);
    }
  }, [messages.length, hasAnimatedIn]);

  const generateAssistantResponse = async (
    userMessage: string,
    currentSessionId: string,
  ) => {
    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: session?.user?.email,
          session_id: currentSessionId,
          message: userMessage,
        }),
      });
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      return {
        response:
          data.response || "Sorry, I had an issue generating a response.",
        ...data,
      };
    } catch (error) {
      return {
        response: `I'm having technical difficulties. (Error: ${error instanceof Error ? error.message : "Unknown"})`,
      };
    }
  };

  const handleTypingEffectChange = useCallback((enabled: boolean) => {
    setTypingEffectEnabled(enabled);
    if (!enabled) {
      toast("Typing effect disabled", {
        description: "Messages will appear instantly",
        action: {
          label: "Undo",
          onClick: () => {
            setTypingEffectEnabled(true);
            toast.success("Typing effect restored!");
          },
        },
        duration: 5000,
      });
    } else {
      toast.success("Typing effect enabled");
    }
  }, []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentMessage(e.target.value);
  }, []);

  const onSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (!currentMessage.trim() || isLoading || !sessionId) return;
      await getSession();
      const messageText = currentMessage.trim();
      const userMessage: Message = {
        id: Date.now(),
        content: messageText,
        role: "user",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setCurrentMessage("");
      setIsLoading(true);

      setTimeout(() => {
        if (chatContainerRef.current) {
          chatContainerRef.current.scrollTop =
            chatContainerRef.current.scrollHeight;
          setShowScrollToBottom(false);
        }
      }, 0);

      const { response: aiResponse, tool_events } =
        await generateAssistantResponse(messageText, sessionId);
      const assistantId = Date.now() + 1;
      const assistantMessage: Message = {
        id: assistantId,
        content: aiResponse,
        role: "assistant",
        timestamp: new Date().toISOString(),
        tool_events,
      };

      setIsLoading(false);

      if (typingEffectEnabled) {
        setMessages((prev) => [...prev, { ...assistantMessage, content: "" }]);
        setCurrentGeneratingId(assistantId);
        const words = aiResponse.split(" ");
        let currentText = "";
        typingIntervalRef.current = setInterval(() => {
          if (words.length > 0) {
            currentText += (currentText ? " " : "") + words.shift();
            setTypingText((prev) => ({ ...prev, [assistantId]: currentText }));
          } else {
            if (typingIntervalRef.current)
              clearInterval(typingIntervalRef.current);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId ? { ...msg, content: aiResponse } : msg,
              ),
            );
            setCurrentGeneratingId(null);
            setTypingText((prev) => {
              const newState = { ...prev };
              delete newState[assistantId];
              return newState;
            });
          }
        }, 50);
      } else {
        setMessages((prev) => [...prev, assistantMessage]);
      }
    },
    [
      currentMessage,
      isLoading,
      sessionId,
      typingEffectEnabled,
      session,
      generateAssistantResponse,
    ],
  );

  const handleStopGeneration = useCallback(() => {
    if (typingIntervalRef.current) clearInterval(typingIntervalRef.current);
    if (currentGeneratingId) {
      const finalContent = typingText[currentGeneratingId] || "";
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === currentGeneratingId
            ? { ...msg, content: finalContent }
            : msg,
        ),
      );
    }
    setCurrentGeneratingId(null);
  }, [currentGeneratingId, typingText]);

  // --- RENDER LOGIC ---
  if (status === "loading" || isPageLoading) {
    return (
      <div
        className="relative min-h-screen w-full overflow-hidden flex items-center justify-center"
        style={{ background: "#1a1b26" }}
      >
        <LoaderThreeDemo />
      </div>
    );
  }

  if (status === "unauthenticated") {
    return null;
  }

  return (
    <SidebarProvider defaultOpen={false}>
      <div
        className="h-screen w-full flex overflow-hidden"
        style={{ background: "#1a1b26" }}
      >
        <ChatSidebar
          sessions={userSessions}
          activeSessionId={sessionId}
          onSelectSession={handleSelectSession}
          onCreateNewSession={handleCreateNewSession}
        />
        <main className="flex-1 flex flex-col h-full overflow-hidden">
          <BackgroundBeams />
          <div
            ref={chatLayoutRef}
            className="relative z-10 flex flex-col h-full p-4 md:p-8 min-h-0"
            style={{ justifyContent: hasAnimatedIn ? "flex-end" : "center" }}
          >
            <SidebarTrigger className="fixed top-4 left-4 z-50 text-[#c0caf5]/60 hover:text-[#c0caf5] hover:bg-[#24283b] rounded p-2 transition-colors" />
            <div
              className={`w-full max-w-6xl mx-auto flex flex-col ${hasAnimatedIn ? "h-full" : "h-auto"} min-h-0`}
            >
              <div
                ref={welcomeHeaderRef}
                style={{
                  display: hasAnimatedIn ? "none" : "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
                className="text-center mb-4 flex-shrink-0"
              >
                <div
                  className="text-3xl md:text-6xl font-bold mb-6"
                  style={{ color: "#c0caf5" }}
                >
                  Chat with a{" "}
                  <FlipWords words={flipWords} className="text-white" /> Luna
                </div>
                <p className="text-neutral-400 mt-2">
                  {apiStatus === "connecting" && "Connecting to server..."}
                  {apiStatus === "connected" && "How can I help you today?"}
                  {apiStatus === "error" && (
                    <span className="text-red-400">
                      Connection failed. Please refresh.
                    </span>
                  )}
                </p>
              </div>

              <div
                ref={chatWrapperRef}
                className="flex-1 flex flex-col min-h-0"
                style={{
                  opacity: hasAnimatedIn ? 1 : 0,
                  maxHeight: hasAnimatedIn ? "100vh" : "0vh",
                }}
              >
                <div
                  className="flex-1 rounded-2xl shadow-2xl flex flex-col min-h-0"
                  style={{
                    background: "transparent",
                    border: "1px solid #414868",
                  }}
                >
                  <div
                    ref={chatContainerRef}
                    className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 chat-container"
                  >
                    {messages.map((message) => (
                      <MessageItem
                        key={message.id}
                        message={message}
                        currentGeneratingId={currentGeneratingId}
                        typingText={typingText}
                      />
                    ))}
                    {isLoading && (
                      <div className="chat chat-start">
                        <div className="chat-image avatar">
                          <div className="w-10 rounded-full overflow-hidden">
                            <img src="/luna-avatar.jpg" alt="Luna Assistant" />
                          </div>
                        </div>
                        <div className="chat-header text-[#c0caf5]">
                          Luna
                          <time className="text-xs opacity-50 ml-2">
                            Typing...
                          </time>
                        </div>
                        <div
                          className="chat-bubble"
                          style={{
                            backgroundColor: "#2f3549",
                            color: "#c0caf5",
                          }}
                        >
                          <span className="loading loading-dots loading-xs"></span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex-shrink-0 pt-4">
                <div className="relative flex items-center gap-3">
                  <div className="flex-1">
                    <PlaceholdersAndVanishInput
                      placeholders={placeholders}
                      onChange={handleChange}
                      onSubmit={onSubmit}
                      value={currentMessage}
                    />
                  </div>
                  {hasAnimatedIn && (
                    <>
                      <div className="flex items-center gap-2 mr-3 transition-opacity duration-500">
                        <label className="switch">
                          <input
                            id="typing-switch"
                            type="checkbox"
                            checked={typingEffectEnabled}
                            onChange={(e) =>
                              handleTypingEffectChange(e.target.checked)
                            }
                          />
                          <span className="slider"></span>
                        </label>
                      </div>
                      {currentGeneratingId !== null && (
                        <Button
                          onClick={handleStopGeneration}
                          variant="destructive"
                          size="icon"
                          title="Stop generation"
                          className="absolute right-20 top-1/2 -translate-y-1/2"
                        >
                          <span className="loading-spinner"></span>
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>

              {showScrollToBottom && (
                <div className="absolute bottom-20 right-4 z-10 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="relative">
                    <Button
                      onClick={() => {
                        smoothScrollToBottom();
                        setNewMessagesCount(0);
                      }}
                      size="icon"
                      className="bg-[#24283b]/90 hover:bg-[#292e42] text-[#c0caf5] shadow-2xl hover:shadow-[#7aa2f7]/20 transition-all duration-300 rounded-full backdrop-blur-sm border border-[#414868]/50 hover:border-[#7aa2f7]/50 w-10 h-10"
                      title={`Scroll to bottom${newMessagesCount > 0 ? ` (${newMessagesCount} new)` : ""}`}
                    >
                      <svg
                        className="size-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 14l-7 7m0 0l-7-7m7 7V3"
                        />
                      </svg>
                    </Button>
                    {newMessagesCount > 0 && (
                      <div className="absolute -top-2 -right-2 bg-[#7aa2f7] text-white text-xs rounded-full min-w-[1.25rem] h-5 flex items-center justify-center px-1 font-medium shadow-lg">
                        {newMessagesCount > 99 ? "99+" : newMessagesCount}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
      <style jsx>{`
        .loading-spinner {
          display: inline-block;
          width: 16px;
          height: 16px;
          border: 8px solid rgba(0, 0, 0, 0.3);
          border-radius: 50%;
          border-top-color: #fff;
          animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
        .switch {
          position: relative;
          display: inline-block;
          width: 50px;
          height: 28px;
        }
        .switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        .slider {
          position: absolute;
          cursor: pointer;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: #414868;
          transition: 0.4s;
          border-radius: 28px;
        }
        .slider:before {
          position: absolute;
          content: "";
          height: 20px;
          width: 20px;
          left: 4px;
          bottom: 4px;
          background-color: #c0caf5;
          transition: 0.4s;
          border-radius: 50%;
        }
        input:checked + .slider {
          background-color: #7aa2f7;
        }
        input:checked + .slider:before {
          transform: translateX(22px);
        }
        .chat-container::-webkit-scrollbar {
          width: 6px;
        }
        .chat-container::-webkit-scrollbar-track {
          background: rgba(65, 72, 104, 0.3);
          border-radius: 3px;
        }
        .chat-container::-webkit-scrollbar-thumb {
          background: rgba(122, 162, 247, 0.5);
          border-radius: 3px;
        }
        .chat-container::-webkit-scrollbar-thumb:hover {
          background: rgba(122, 162, 247, 0.7);
        }
      `}</style>
      <Toaster position="top-right" />
    </SidebarProvider>
  );
}
