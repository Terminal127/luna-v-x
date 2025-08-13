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
import { FlipWords } from "../../components/ui/flip-words";
// CORRECT Anime.js v4 named imports
import { animate, stagger } from "animejs";
import { cva, type VariantProps } from "class-variance-authority";
import { twMerge } from "tailwind-merge";
import { clsx } from "clsx";
import MessageItem from "./MessageItem";
import { LoaderThree } from "../../components/ui/loader";

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
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [typingEffectEnabled, setTypingEffectEnabled] = useState(true);

  const flipWords = ["helpful", "creative", "intelligent", "powerful"];

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

  useEffect(() => {
    const initSession = async () => {
      try {
        await fetch("http://localhost:8000/health");
        const response = await fetch("http://localhost:8000/api/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const data = await response.json();
        setSessionId(data.session_id);
        setApiStatus("connected");
      } catch (error) {
        setApiStatus("error");
      } finally {
        // Simulate a delay for demonstration purposes
        setTimeout(() => {
          setIsPageLoading(false);
        }, 1000); // Adjust the delay as needed
      }
    };
    initSession();
  }, []);

  const smoothScrollToBottom = useCallback(() => {
    if (!chatContainerRef.current) return;
    setTimeout(() => {
      if (chatContainerRef.current) {
        animate(chatContainerRef.current, {
          scrollTop: chatContainerRef.current.scrollHeight,
          duration: 500,
          easing: "easeOutCubic",
        });
      }
    }, 0);
  }, []);

  useEffect(() => {
    smoothScrollToBottom();
  }, [messages, typingText, smoothScrollToBottom]);

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

  useEffect(() => {
    if (messages.length === 1 && chatLayoutRef.current) {
      animate(welcomeHeaderRef.current, {
        opacity: 0,
        duration: 400,
        easing: "easeOutCubic",
        complete: () => {
          if (welcomeHeaderRef.current) {
            welcomeHeaderRef.current.style.display = "none";
          }
        },
      });
      animate(chatLayoutRef.current, {
        justifyContent: ["center", "flex-end"],
        duration: 200,
        easing: "easeInOutSine",
      });
      animate(chatWrapperRef.current, {
        maxHeight: ["0vh", "100vh"],
        opacity: [0, 1],
        duration: 500,
        easing: "easeInOutSine",
      });
    }
  }, [messages.length]);

  const generateAssistantResponse = async (
    userMessage: string,
    sessionId: string,
  ) => {
    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: userMessage }),
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

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentMessage(e.target.value);
  }, []);

  const onSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (!currentMessage.trim() || isLoading) return;

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

      // Capture tool_events from the response
      const { response: aiResponse, tool_events } =
        await generateAssistantResponse(messageText, sessionId);
      const assistantId = Date.now() + 1;

      // Pass tool_events to the new message object
      const assistantMessage: Message = {
        id: assistantId,
        content: aiResponse || "Sorry, I had an issue generating a response.",
        role: "assistant",
        timestamp: new Date().toISOString(),
        tool_events: tool_events,
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
    },
    [currentMessage, isLoading, sessionId, typingEffectEnabled],
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

  if (isPageLoading) {
    return (
      <div
        className="relative min-h-screen w-full overflow-hidden flex items-center justify-center"
        style={{ background: "#1a1b26" }}
      >
        <LoaderThreeDemo />
      </div>
    );
  }

  return (
    <div
      className="relative min-h-screen w-full overflow-hidden"
      style={{ background: "#1a1b26" }}
    >
      <BackgroundBeams />
      <div
        ref={chatLayoutRef}
        className="relative z-10 flex flex-col h-screen p-4 md:p-8"
        style={{ justifyContent: "center" }}
      >
        <div
          className={`w-full max-w-6xl mx-auto flex flex-col ${
            messages.length > 0 ? "h-full" : "h-auto"
          }`}
        >
          <div
            ref={welcomeHeaderRef}
            className="text-center mb-4 flex-shrink-0"
          >
            <div
              className="text-3xl md:text-6xl font-bold mb-6"
              style={{ color: "#c0caf5" }}
            >
              Chat with a
              <FlipWords words={flipWords} className="text-white" />
              Luna
            </div>
            <p className="text-neutral-400 mt-2">
              {apiStatus === "connecting"
                ? "Connecting..."
                : "How can I help you today?"}
            </p>
          </div>

          <div
            ref={chatWrapperRef}
            className="flex-1 flex flex-col min-h-0"
            style={{ opacity: 0, maxHeight: "0vh" }}
          >
            <div
              className="flex-1 rounded-2xl shadow-2xl flex flex-col min-h-0"
              style={{
                // background: "rgba(36, 40, 59, 0.6)",
                // this is the code where the chat container is defined
                background: "transparent",
                border: "1px solid #414868",
                // backdropFilter: "blur(12px)",
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
                  ref={inputRef}
                />
              </div>

              {/* ✅ MODIFIED: The toggle switch is now conditionally rendered */}
              {messages.length > 0 && (
                <div className="flex items-center gap-2 mr-3 transition-opacity duration-500">
                  <span
                    className="text-sm text-neutral-400 font-sans"
                    htmlFor="typing-switch"
                  ></span>
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
              )}

              {currentGeneratingId !== null && (
                <Button
                  onClick={handleStopGeneration}
                  variant="destructive"
                  size="icon" // Use the new "icon" size
                  title="Stop generation"
                  // Add absolute positioning classes
                  className="absolute right-20 top-1/2 -translate-y-1/2"
                >
                  <span className="loading-spinner"></span>
                  {/* REMOVE THE TEXT SPAN: <span className="hidden md:inline">Stop</span> */}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
      <style jsx>{`
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
    </div>
  );
}
