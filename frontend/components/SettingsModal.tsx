"use client";

import { toast } from "sonner";
import { X, Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import React from "react";
import { Toaster } from "@/components/ui/sonner";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ModelConfig {
  company: string;
  models: string[];
}

interface BackendConfig {
  success: boolean;
  message: string;
  current_config: {
    model_name: string;
    temperature: number;
    api_key: string;
    model_initialized: boolean;
  };
}

const modelConfigs: ModelConfig[] = [
  {
    company: "Google",
    models: [
      "gemini-2.5-flash-lite",
      "gemini-2.0-flash",
      "gemini-2.5-pro",
      "gemini-2.5-flash",
    ],
  },
  {
    company: "OpenAI",
    models: ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"],
  },
  {
    company: "Anthropic",
    models: [
      "claude-3-opus",
      "claude-3-sonnet",
      "claude-3-haiku",
      "claude-3.5-sonnet",
    ],
  },
];

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [apiKey, setApiKey] = useState("");
  const [selectedCompany, setSelectedCompany] = useState("Google");
  const [selectedModel, setSelectedModel] = useState(""); // Changed initial state to empty string
  const [temperature, setTemperature] = useState(0.3);
  const [showApiKey, setShowApiKey] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "success" | "error">(
    "idle",
  );
  const [currentConfig, setCurrentConfig] = useState<
    BackendConfig["current_config"] | null
  >(null);

  // Load current configuration when modal opens
  const loadCurrentConfig = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/config/model");
      if (response.ok) {
        const data: BackendConfig = await response.json();
        if (data.success && data.current_config) {
          setCurrentConfig(data.current_config);
          setSelectedModel(data.current_config.model_name);
          setTemperature(data.current_config.temperature);
          // Set company based on model name
          if (data.current_config.model_name.includes("gemini")) {
            setSelectedCompany("Google");
          }
        }
      }
    } catch (error) {
      console.error("Failed to load current config:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Load config when modal opens
  React.useEffect(() => {
    if (isOpen) {
      loadCurrentConfig();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCompanyChange = (company: string) => {
    setSelectedCompany(company);
    setSelectedModel(""); // Reset model when company changes
  };

  const getAvailableModels = () => {
    const config = modelConfigs.find(
      (config) => config.company === selectedCompany,
    );
    return config?.models || [];
  };

  const handleSave = async () => {
    if (!selectedModel) {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
      return;
    }

    setIsSaving(true);
    setSaveStatus("idle");

    try {
      const updateData: any = {
        model_name: selectedModel,
        temperature: temperature,
      };

      // Only include API key if it's provided
      if (apiKey.trim()) {
        updateData.api_key = apiKey;
      }

      const response = await fetch("http://localhost:8000/api/config/model", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(updateData),
      });

      const data: BackendConfig = await response.json();
      console.log("Backend response:", data);

      if (data && data.success) {
        toast.success("Changes saved Successfully");
        setSaveStatus("success");
        setCurrentConfig(data.current_config);
        setTimeout(() => {
          setSaveStatus("idle");
          onClose();
        }, 1500);
      } else {
        setSaveStatus("error");
        console.error("Backend error:", data?.message || "Unknown error", data);
      }
    } catch (error) {
      console.error("Failed to update configuration:", error);
      setSaveStatus("error");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center"
        style={{ backgroundColor: "rgba(0, 0, 0, 0.6)" }}
      >
        {/* Backdrop - click to close */}
        <div className="absolute inset-0" onClick={onClose} />

        {/* Modal Content */}
        <div
          className="relative bg-[#24283b] border border-[#414868] rounded-lg shadow-2xl w-full max-w-2xl mx-4 p-6 max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-[#c0caf5]">Settings</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-[#414868] rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-[#c0caf5]" />
            </button>
          </div>

          {/* Settings Content */}
          <div className="space-y-6">
            {/* Model Configuration Section */}
            <div className="p-4 bg-[#1a1b26] rounded-lg border border-[#414868]/50">
              <h3 className="text-[#c0caf5] font-medium mb-4">
                Model Configuration
              </h3>

              {/* Company Selection */}
              <div className="mb-4">
                <label className="block text-[#c0caf5] text-sm font-medium mb-2">
                  AI Provider
                </label>
                <select
                  value={selectedCompany}
                  onChange={(e) => handleCompanyChange(e.target.value)}
                  className="w-full p-3 bg-[#24283b] border border-[#414868] rounded-lg text-[#c0caf5] focus:border-[#7aa2f7] focus:outline-none transition-colors"
                >
                  <option value="">Select Provider</option>
                  {modelConfigs.map((config) => (
                    <option key={config.company} value={config.company}>
                      {config.company}
                    </option>
                  ))}
                </select>
              </div>

              {/* Model Selection */}
              <div className="mb-4">
                <label className="block text-[#c0caf5] text-sm font-medium mb-2">
                  Model
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  disabled={!selectedCompany}
                  className="w-full p-3 bg-[#24283b] border border-[#414868] rounded-lg text-[#c0caf5] focus:border-[#7aa2f7] focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">Select Model</option>
                  {getAvailableModels().map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </div>

              {/* Temperature Setting */}
              <div className="mb-4">
                <label className="block text-[#c0caf5] text-sm font-medium mb-2">
                  Temperature ({temperature})
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full h-2 bg-[#414868] rounded-lg appearance-none cursor-pointer slider-thumb"
                />
                <div className="flex justify-between text-xs text-[#c0caf5]/60 mt-1">
                  <span>Precise (0.0)</span>
                  <span>Creative (1.0)</span>
                </div>
              </div>

              {/* API Key Input */}
              <div className="mb-4">
                <label className="block text-[#c0caf5] text-sm font-medium mb-2">
                  API Key (Optional - leave empty to keep current)
                </label>
                <div className="relative">
                  <input
                    type={showApiKey ? "text" : "password"}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={`Enter new ${selectedCompany} API key (optional)`}
                    className="w-full p-3 pr-12 bg-[#24283b] border border-[#414868] rounded-lg text-[#c0caf5] placeholder-[#c0caf5]/40 focus:border-[#7aa2f7] focus:outline-none transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#c0caf5]/60 hover:text-[#c0caf5] transition-colors"
                  >
                    {showApiKey ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Current Configuration Display */}
              {isLoading ? (
                <div className="mt-4 p-3 bg-[#414868]/20 rounded-lg border border-[#414868]/30">
                  <div className="flex items-center gap-2 text-[#c0caf5]/70">
                    <div className="w-4 h-4 border-2 border-[#7aa2f7]/30 border-t-[#7aa2f7] rounded-full animate-spin"></div>
                    Loading current configuration...
                  </div>
                </div>
              ) : currentConfig ? (
                <div className="mt-4 p-3 bg-[#414868]/20 rounded-lg border border-[#414868]/30">
                  <h4 className="text-[#c0caf5] text-sm font-medium mb-2">
                    Current Backend Configuration:
                  </h4>
                  <div className="text-xs text-[#c0caf5]/70 space-y-1">
                    <div>
                      Model:{" "}
                      <span className="text-[#7aa2f7]">
                        {currentConfig.model_name}
                      </span>
                    </div>
                    <div>
                      Temperature:{" "}
                      <span className="text-[#7aa2f7]">
                        {currentConfig.temperature}
                      </span>
                    </div>
                    <div>
                      API Key:{" "}
                      <span className="text-[#7aa2f7]">
                        {currentConfig.api_key ? "Set" : "Not set"}
                      </span>
                    </div>
                    <div>
                      Status:{" "}
                      <span
                        className={
                          currentConfig.model_initialized
                            ? "text-[#9ece6a]"
                            : "text-[#f7768e]"
                        }
                      >
                        {currentConfig.model_initialized
                          ? "✓ Initialized"
                          : "✗ Not initialized"}
                      </span>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 flex items-center justify-between">
            {/* Status Message */}
            <div className="flex-1">
              {currentConfig && (
                <span className="text-[#9ece6a] text-sm">
                  ✓ Backend connected - Model: {currentConfig.model_name}
                </span>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-[#c0caf5]/60 hover:text-[#c0caf5] hover:bg-[#414868] rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-2 bg-[#7aa2f7] hover:bg-[#7aa2f7]/90 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSaving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Saving...
                  </>
                ) : (
                  "Save Changes"
                )}
              </button>
            </div>
          </div>
        </div>

        {/* CSS Styles */}
        <style jsx>{`
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

          /* Range slider styling */
          .slider-thumb::-webkit-slider-thumb {
            appearance: none;
            height: 20px;
            width: 20px;
            border-radius: 50%;
            background: #7aa2f7;
            cursor: pointer;
            border: 2px solid #1a1b26;
          }

          .slider-thumb::-moz-range-thumb {
            height: 20px;
            width: 20px;
            border-radius: 50%;
            background: #7aa2f7;
            cursor: pointer;
            border: 2px solid #1a1b26;
          }
        `}</style>
      </div>
      <Toaster />
    </>
  );
}
