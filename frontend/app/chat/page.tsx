"use client";

import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import { BackgroundBeams } from "../../components/ui/background-beams";
import { PlaceholdersAndVanishInput } from "../../components/ui/placeholders-and-vanish-input";
import { gsap } from "gsap";
import { ScrollToPlugin } from "gsap/ScrollToPlugin";
import { cva, type VariantProps } from "class-variance-authority";
import { twMerge } from "tailwind-merge";
import { clsx } from "clsx";
import { IconPlayerStop } from "@tabler/icons-react";
import MessageItem from "./MessageItem";

gsap.registerPlugin(ScrollToPlugin);

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-full text-sm font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none hover:scale-105 active:scale-95",
  {
    variants: {
      variant: {
        default:
          "bg-blue-500 text-white shadow-lg shadow-blue-500/30 hover:bg-blue-500/90",
        destructive:
          "bg-gradient-to-r from-red-500 to-orange-500 text-white shadow-lg shadow-red-500/40 hover:opacity-90",
        secondary:
          "bg-neutral-700/80 text-neutral-200 border border-neutral-600/80 shadow-lg shadow-neutral-900/40 hover:bg-neutral-700",
        premium:
          "bg-gradient-to-r from-blue-400 to-purple-500 text-white border-0 shadow-lg shadow-purple-500/30 hover:opacity-90",
      },
      size: {
        default: "h-12 px-6",
        icon: "h-12 w-12",
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

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [sessionId, setSessionId] = useState<string>("");
  const [apiStatus, setApiStatus] = useState<
    "connecting" | "connected" | "error"
  >("connecting");
  const [currentGeneratingId, setCurrentGeneratingId] = useState<number | null>(
    null,
  );
  const [typingText, setTypingText] = useState<{ [key: number]: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [typingEffectEnabled, setTypingEffectEnabled] = useState(true);

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const typingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastMessageCountRef = useRef<number>(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const placeholders = useMemo(
    () => [
      "Ask anything...",
      "How can I help you today?",
      "What would you like to know?",
      "Type your message here...",
      "Start a conversation...",
    ],
    [],
  );

  useEffect(() => {
    const initSession = async () => {
      try {
        const healthResponse = await fetch("http://localhost:8000/health");
        if (!healthResponse.ok) throw new Error("API health check failed");
        const response = await fetch("http://localhost:8000/api/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const data = await response.json();
        setSessionId(data.session_id);
        setApiStatus("connected");
      } catch (error) {
        console.error("Failed to connect to API:", error);
        setApiStatus("error");
        setSessionId(Date.now().toString());
      }
    };
    initSession();
  }, []);

  const smoothScrollToBottom = () => {
    if (chatContainerRef.current) {
      const container = chatContainerRef.current;
      gsap.to(container, {
        scrollTop: container.scrollHeight,
        duration: 0.6,
        ease: "power3.out",
      });
    }
  };

  useEffect(() => {
    const scrollTimeout = setTimeout(() => smoothScrollToBottom(), 100);
    return () => clearTimeout(scrollTimeout);
  }, [messages, typingText]);

  useEffect(() => {
    if (messages.length > lastMessageCountRef.current) {
      const newMessageCount = messages.length - lastMessageCountRef.current;
      const messageElements = Array.from(
        document.querySelectorAll("[data-message-id]"),
      ).slice(-newMessageCount);

      gsap.from(messageElements, {
        opacity: 0,
        y: 30,
        scale: 0.95,
        duration: 0.8,
        ease: "power3.out",
        stagger: 0.15,
      });
      lastMessageCountRef.current = messages.length;
    }
  }, [messages]);

  const generateAssistantResponse = async (
    userMessage: string,
    sessionId: string,
  ): Promise<{ response: string; tool_events?: ToolEvent[] }> => {
    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: userMessage }),
      });
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      if (data.error) throw new Error(data.error);
      return {
        response: data.response || "I'm sorry, I couldn't generate a response.",
        tool_events: data.tool_events,
      };
    } catch (error) {
      console.error("Error calling LangChain API:", error);
      return {
        response: `I'm experiencing technical difficulties. Please try again later. (Error: ${
          error instanceof Error ? error.message : "Unknown error"
        })`,
      };
    }
  };

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentMessage(e.target.value);
  }, []);

  const onSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (!currentMessage.trim() || isLoading || currentGeneratingId) return;

      const messageText = currentMessage.trim();
      setCurrentMessage("");

      const userMessage: Message = {
        id: Date.now(),
        content: messageText,
        role: "user",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        const { response: aiResponse, tool_events } =
          await generateAssistantResponse(messageText, sessionId);
        const assistantId = Date.now() + 1;

        const assistantMessage: Message = {
          id: assistantId,
          content: "",
          role: "assistant",
          timestamp: new Date().toISOString(),
          tool_events,
        };
        setMessages((prev) => [...prev, assistantMessage]);
        setCurrentGeneratingId(assistantId);
        setIsLoading(false);

        if (typingEffectEnabled) {
          const words = aiResponse.split(" ");
          let currentText = "";
          typingIntervalRef.current = setInterval(() => {
            if (words.length > 0) {
              currentText += (currentText ? " " : "") + words.shift();
              setTypingText((prev) => ({
                ...prev,
                [assistantId]: currentText,
              }));
            } else {
              if (typingIntervalRef.current)
                clearInterval(typingIntervalRef.current);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, content: aiResponse }
                    : msg,
                ),
              );
              setCurrentGeneratingId(null);
            }
          }, 50);
        } else {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId ? { ...msg, content: aiResponse } : msg,
            ),
          );
          setCurrentGeneratingId(null);
        }
      } catch (error) {
        console.error("Failed to get AI response:", error);
        const errorMessage: Message = {
          id: Date.now() + 1,
          content:
            "I'm sorry, I'm having trouble connecting. Please try again.",
          role: "assistant",
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
        setIsLoading(false);
        setCurrentGeneratingId(null);
      }
    },
    [
      currentMessage,
      isLoading,
      currentGeneratingId,
      sessionId,
      typingEffectEnabled,
    ],
  );

  const handleStopGeneration = useCallback(() => {
    if (currentGeneratingId) {
      if (typingIntervalRef.current) {
        clearInterval(typingIntervalRef.current);
        typingIntervalRef.current = null;
      }
      const finalContent = typingText[currentGeneratingId] || "";
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === currentGeneratingId
            ? { ...msg, content: finalContent }
            : msg,
        ),
      );
      setCurrentGeneratingId(null);
      setTypingText((prev) => {
        const newState = { ...prev };
        delete newState[currentGeneratingId];
        return newState;
      });
    }
  }, [currentGeneratingId, typingText]);

  return (
    <div
      className="relative min-h-screen w-full overflow-hidden"
      style={{
        minHeight: "100vh",
        minWidth: "100vw",
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "#1a1b26",
      }}
    >
      <BackgroundBeams />
      <div className="relative z-10 flex flex-col h-screen p-4 md:p-8 lg:p-14">
        {messages.length === 0 && (
          <div
            className="flex-shrink-0 p-6 text-center mb-4 rounded-2xl header-fade-in"
            style={{
              borderBottom: "1px solid #414868",
              background: "rgba(36, 40, 59, 0.6)",
              border: "1px solid #414868",
              backdropFilter: "blur(12px)",
            }}
          >
            <h1
              className="text-2xl md:text-3xl font-bold"
              style={{ color: "#c0caf5" }}
            >
              Chat with Luna AI
            </h1>
          </div>
        )}

        <div className="flex-1 flex flex-col overflow-hidden">
          <div
            className="flex-1 backdrop-blur-sm rounded-2xl shadow-2xl flex flex-col min-h-0 chat-container-enter"
            style={{
              background: "rgba(36, 40, 59, 0.6)",
              border: "1px solid #414868",
              backdropFilter: "blur(12px)",
            }}
          >
            <div
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 chat-container"
              style={{ scrollBehavior: "smooth" }}
            >
              {messages.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div
                    className="text-center welcome-animation"
                    style={{ color: "#7aa2f7" }}
                  >
                    {apiStatus === "connecting" && (
                      <>
                        <h3 className="text-lg font-medium mb-2">
                          Connecting to Luna AI...
                        </h3>
                        <div className="flex justify-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
                        </div>
                      </>
                    )}
                    {apiStatus === "connected" && (
                      <>
                        <h3 className="text-lg font-medium mb-2">
                          Start a conversation
                        </h3>
                        <p className="text-sm opacity-80">
                          Ask me anything and I&apos;ll do my best to help!
                        </p>
                      </>
                    )}
                    {apiStatus === "error" && (
                      <>
                        <h3 className="text-lg font-medium mb-2 text-red-400">
                          Connection Error
                        </h3>
                        <p className="text-sm text-red-300">
                          Unable to connect to the AI service.
                        </p>
                      </>
                    )}
                  </div>
                </div>
              ) : (
                messages.map((message) => (
                  <MessageItem
                    key={message.id}
                    message={message}
                    currentGeneratingId={currentGeneratingId}
                    typingText={typingText}
                  />
                ))
              )}
            </div>

            <div
              className="flex-shrink-0 p-4 md:p-6 input-area"
              style={{
                borderTop: "1px solid #414868",
                background: "rgba(26, 27, 38, 0.8)",
                backdropFilter: "blur(8px)",
              }}
            >
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <PlaceholdersAndVanishInput
                    placeholders={placeholders}
                    onChange={handleChange}
                    onSubmit={onSubmit}
                    ref={inputRef}
                  />
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className="text-sm text-neutral-400 font-sans"
                    htmlFor="typing-switch"
                  >
                    Animate
                  </span>
                  <label className="switch">
                    <input
                      id="typing-switch"
                      type="checkbox"
                      checked={typingEffectEnabled}
                      onChange={(e) => setTypingEffectEnabled(e.target.checked)}
                    />
                    <span className="slider"></span>
                  </label>
                </div>

                {/* --- MODIFIED STOP BUTTON --- */}
                {currentGeneratingId !== null && (
                  <Button
                    onClick={handleStopGeneration}
                    variant="destructive"
                    size="default"
                    className="gap-2"
                    title="Stop generation"
                  >
                    <span className="loading-spinner"></span>
                    <span className="hidden md:inline">Stop</span>
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      <style jsx>{`
        /* --- NEW CSS FOR LOADING SPINNER --- */
        .loading-spinner {
          display: inline-block;
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-radius: 50%;
          border-top-color: #fff;
          animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        /* --- CSS FOR THE SLIDER TOGGLE --- */
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

        .claude-cursor {
          animation: claude-blink 1.2s ease-in-out infinite;
        }
        @keyframes claude-blink {
          0%,
          50% {
            opacity: 1;
          }
          51%,
          100% {
            opacity: 0;
          }
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
        .welcome-animation {
          animation: welcome-fade-in 1s ease-out;
        }
        @keyframes welcome-fade-in {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .header-fade-in {
          animation: header-slide-down 0.8s ease-out;
        }
        @keyframes header-slide-down {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .chat-container-enter {
          animation: container-scale-in 0.6s ease-out;
        }
        @keyframes container-scale-in {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
      `}</style>
    </div>
  );
}
