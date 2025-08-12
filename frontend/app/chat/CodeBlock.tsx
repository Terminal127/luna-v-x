"use client";
import React from "react";
// Import the original Aceternity UI component
import { CodeBlock as AceternityCodeBlock } from "@/components/ui/code-block";

// This is the adapter component that react-markdown will use
const CodeBlockAdapter = ({ className, children, ...props }: any) => {
  // Render a simple `code` tag for inline code
  if (props.inline) {
    return (
      <code
        className="bg-neutral-700/60 px-1.5 py-0.5 rounded text-sm font-mono border border-neutral-600/50"
        style={{ color: "#f7768e" }}
        {...props}
      >
        {children}
      </code>
    );
  }

  // For code blocks, parse the language and optional filename
  const match = /language-(\w+)(?::([\w.-]+))?/.exec(className || "");
  const language = match ? match[1] : "plaintext";
  const filename = match ? match[2] : "file"; // Default filename if none provided
  const code = String(children).replace(/\n$/, "");

  // Render the real Aceternity UI component with the parsed props
  return (
    <AceternityCodeBlock language={language} code={code} filename={filename} />
  );
};

export default CodeBlockAdapter;
