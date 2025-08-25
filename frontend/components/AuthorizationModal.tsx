"use client";
import { useState, useEffect } from "react";
import { ShieldAlert, Edit, X } from "lucide-react";

// --- Interfaces ---
interface AuthRequest {
  session_id: string;
  tool_name: string;
  tool_args: Record<string, any>;
}

interface AuthorizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  authRequest: AuthRequest | null;
  onSubmit: (
    authorization: "A" | "D",
    modifiedArgs?: Record<string, any>,
  ) => void;
}

const AUTH_API_URL = process.env.NEXT_PUBLIC_TOOL_API_BASE_URL; // e.g., 'http://localhost:9000/auth'

// --- The Modal Component ---
export function AuthorizationModal({
  isOpen,
  onClose,
  authRequest,
  onSubmit,
}: AuthorizationModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<Record<string, any>>({});

  // When a new request comes in, reset the form state
  useEffect(() => {
    if (authRequest) {
      setFormData(authRequest.tool_args);
      setIsEditing(false); // Reset to read-only view
    }
  }, [authRequest]);

  if (!isOpen || !authRequest) {
    return null;
  }

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (authorization: "A" | "D") => {
    const finalArgs = isEditing ? formData : undefined;
    onSubmit(authorization, finalArgs);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 backdrop-blur-sm">
      <div className="bg-gray-800 border border-gray-700 text-white rounded-lg shadow-xl p-6 w-full max-w-lg transform transition-all">
        {/* Header */}
        <div className="flex items-center border-b border-gray-600 pb-3 mb-4">
          <ShieldAlert className="text-yellow-400 h-6 w-6 mr-3" />
          <h2 className="text-xl font-bold">Authorization Required</h2>
          <button
            onClick={onClose}
            className="ml-auto text-gray-400 hover:text-white"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div>
          <p className="mb-2 text-gray-300">
            The AI agent wants to run the tool:{" "}
            <strong className="font-mono text-cyan-400">
              {authRequest.tool_name}
            </strong>
          </p>

          {/* View / Edit Toggle */}
          {!isEditing ? (
            // READ-ONLY VIEW
            <div>
              <p className="font-semibold mb-2">
                With the following parameters:
              </p>
              <div className="bg-gray-900 rounded-md p-3 max-h-60 overflow-y-auto text-sm space-y-2">
                {Object.entries(authRequest.tool_args).map(([key, value]) => (
                  <div key={key}>
                    <strong className="text-gray-400">{key}:</strong>
                    <pre className="whitespace-pre-wrap text-white font-mono text-xs pl-2">
                      {String(value)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            // EDITABLE VIEW
            <div>
              <p className="font-semibold mb-2">Modify parameters:</p>
              <div className="bg-gray-900 rounded-md p-3 max-h-60 overflow-y-auto space-y-4">
                {Object.entries(formData).map(([key, value]) => (
                  <div key={key} className="flex flex-col">
                    <label
                      htmlFor={`input-${key}`}
                      className="text-gray-400 mb-1 font-bold text-sm"
                    >
                      {key}
                    </label>
                    {String(value).length > 60 ||
                    String(value).includes("\n") ? (
                      <textarea
                        id={`input-${key}`}
                        name={key}
                        value={value}
                        onChange={handleInputChange}
                        className="bg-gray-700 border border-gray-600 rounded p-2 text-white font-mono text-sm w-full focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                        rows={4}
                      />
                    ) : (
                      <input
                        id={`input-${key}`}
                        name={key}
                        type="text"
                        value={value}
                        onChange={handleInputChange}
                        className="bg-gray-700 border border-gray-600 rounded p-2 text-white font-mono text-sm w-full focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Buttons */}
        <div className="flex justify-end gap-3 mt-5">
          {isEditing ? (
            <>
              <button
                onClick={() => setIsEditing(false)}
                className="bg-gray-600 hover:bg-gray-500 font-bold py-2 px-4 rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleSubmit("A")}
                className="bg-green-600 hover:bg-green-500 font-bold py-2 px-4 rounded transition-colors"
              >
                Approve with Changes
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => handleSubmit("D")}
                className="bg-red-600 hover:bg-red-500 font-bold py-2 px-4 rounded transition-colors"
              >
                Deny
              </button>
              <button
                onClick={() => setIsEditing(true)}
                className="bg-blue-600 hover:bg-blue-500 font-bold py-2 px-4 rounded transition-colors flex items-center"
              >
                <Edit size={16} className="mr-2" /> Modify
              </button>
              <button
                onClick={() => handleSubmit("A")}
                className="bg-green-600 hover:bg-green-500 font-bold py-2 px-4 rounded transition-colors"
              >
                Approve
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
