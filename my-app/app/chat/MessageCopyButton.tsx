"use client";
import React, { useState } from "react";

const MessageCopyButton = ({ content }: { content: string }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy message: ", err);
    }
  };
  return (
    <button
      onClick={handleCopy}
      className="opacity-0 group-hover:opacity-100 transition-all duration-200 p-1.5 rounded hover:bg-neutral-700/50 text-neutral-400 hover:text-neutral-200 ml-2"
      title={copied ? "Copied!" : "Copy message"}
    >
      {/* SVG Icons */}
    </button>
  );
};

export default MessageCopyButton;
