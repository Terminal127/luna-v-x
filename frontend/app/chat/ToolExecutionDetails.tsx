"use client";
import React, { useState } from "react";

interface ToolEvent {
  tool: string;
  args: { [key: string]: any };
  duration_ms: number;
  success: boolean;
  error: string | null;
  output_excerpt: string;
}

const ToolExecutionDetails = ({ toolEvents }: { toolEvents: ToolEvent[] }) => {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div
      className="my-2 p-2 rounded-lg"
      style={{ background: "rgba(0,0,0,0.2)" }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="text-xs text-blue-400 hover:text-blue-300 w-full text-left flex items-center"
      >
        <span className="font-semibold">
          Tool Used: {toolEvents.map((event) => event.tool).join(", ")}
        </span>
        <svg
          className={`w-4 h-4 ml-2 transform transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {isOpen && (
        <div className="mt-2 p-2 rounded bg-neutral-800 text-xs space-y-2">
          {toolEvents.map((event, index) => (
            <div
              key={index}
              className="mb-2 last:mb-0 border-b border-neutral-700 last:border-b-0 pb-2 last:pb-0"
            >
              <p>
                <strong>Tool:</strong> {event.tool}
              </p>
              <div>
                <strong>Arguments:</strong>
                <pre className="whitespace-pre-wrap p-1 mt-1 bg-black rounded font-mono text-xs">
                  {JSON.stringify(event.args, null, 2)}
                </pre>
              </div>
              <p>
                <strong>Duration:</strong> {event.duration_ms}ms
              </p>
              <p>
                <strong>Success:</strong> {event.success ? "Yes" : "No"}
              </p>
              {event.error && (
                <p>
                  <strong>Error:</strong> {event.error}
                </p>
              )}
              <div>
                <strong>Output Excerpt:</strong>
                <div className="p-1 mt-1 bg-black rounded">
                  <p className="font-mono text-xs">{event.output_excerpt}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ToolExecutionDetails;
