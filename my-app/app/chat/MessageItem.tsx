"use client";
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { IconUser, IconRobot } from "@tabler/icons-react";
import { markdownComponents } from "./markdownComponents";
import ToolExecutionDetails from "./ToolExecutionDetails";
import MessageCopyButton from "./MessageCopyButton";

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

const MessageItem = React.memo(function MessageItem({
  message,
  currentGeneratingId,
  typingText,
}: {
  message: Message;
  currentGeneratingId: number | null;
  typingText: { [key: number]: string };
}) {
  const isUser = message.role === "user";
  const chatAlignment = isUser ? "chat-end" : "chat-start";
  const userName = isUser ? "You" : "Luna";

  return (
    <div className={`chat ${chatAlignment}`} data-message-id={message.id}>
      <div className="chat-image avatar">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center"
          style={{
            backgroundColor: isUser ? "#7aa2f7" : "#9ece6a",
            color: "#1a1b26",
          }}
        ></div>
      </div>

      <div className="chat-header" style={{ color: "#c0caf5" }}>
        {userName}
        <time className="text-xs ml-2" style={{ color: "#565f89" }}>
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </time>
      </div>

      <div
        className={`chat-bubble ${isUser ? "chat-bubble-info" : ""}`}
        style={{
          backgroundColor: isUser ? "#7aa2f7" : "#2f3549",
          color: isUser ? "#1a1b26" : "#c0caf5",
        }}
      >
        {message.role === "assistant" ? (
          <div className="leading-relaxed">
            {message.tool_events && message.tool_events.length > 0 && (
              <ToolExecutionDetails toolEvents={message.tool_events} />
            )}

            {currentGeneratingId === message.id ? (
              <div className="typing-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents as any}
                >
                  {typingText[message.id] || ""}
                </ReactMarkdown>
              </div>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={markdownComponents as any}
              >
                {message.content}
              </ReactMarkdown>
            )}

            {currentGeneratingId !== message.id && message.content && (
              <div className="absolute top-2 right-2">
                <MessageCopyButton content={message.content} />
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm leading-relaxed font-medium">
            {message.content}
          </p>
        )}
      </div>

      {/* Keep only Delivered footer */}
      <div className="chat-footer font-medium" style={{ color: "#565f89" }}>
        Delivered
      </div>
    </div>
  );
});

MessageItem.displayName = "MessageItem";
export default MessageItem;
