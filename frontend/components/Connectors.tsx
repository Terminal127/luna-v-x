"use client";

import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { signIn } from "next-auth/react"; // IMPORTANT: Use signIn from next-auth/react

// Connector interface
interface Connector {
  id: string;
  name: string;
  description: string;
  iconUrl: string;
  scope: string;
}

// Props interface
interface ConnectorsProps {
  isOpen: boolean;
  onClose: () => void;
}

// Google Suite Connectors (remains the same)
const googleSuiteConnectors: Connector[] = [
  {
    id: "gmail",
    name: "Gmail",
    description: "Read, send, and manage your emails",
    iconUrl:
      "https://img.icons8.com/?size=100&id=37246&format=png&color=000000",
    scope:
      "openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
  },
  {
    id: "google-drive",
    name: "Google Drive",
    description: "Access and manage files in Google Drive",
    iconUrl:
      "https://ssl.gstatic.com/docs/doclist/images/drive_2022q3_32dp.png",
    scope: "openid email profile https://www.googleapis.com/auth/drive",
  },
  {
    id: "google-calendar",
    name: "Google Calendar",
    description: "View and manage your calendar events",
    iconUrl:
      "https://img.icons8.com/?size=100&id=WKF3bm1munsk&format=png&color=000000",
    scope: "openid email profile https://www.googleapis.com/auth/calendar",
  },
  {
    id: "google-meet",
    name: "Google Meet",
    description: "Create and manage video meetings",
    iconUrl:
      "https://img.icons8.com/?size=100&id=pE97I4t7Il9M&format=png&color=000000",
    scope:
      "openid email profile https://www.googleapis.com/auth/meetings.space.created",
  },
  {
    id: "google-docs",
    name: "Google Docs",
    description: "Create and edit documents",
    iconUrl:
      "https://img.icons8.com/?size=100&id=30464&format=png&color=000000",
    scope: "openid email profile https://www.googleapis.com/auth/documents",
  },
  {
    id: "google-sheets",
    name: "Google Sheets",
    description: "Create and edit spreadsheets",
    iconUrl:
      "https://img.icons8.com/?size=100&id=30461&format=png&color=000000",
    scope: "openid email profile https://www.googleapis.com/auth/spreadsheets",
  },
  {
    id: "google-slides",
    name: "Google Slides",
    description: "Create and edit presentations",
    iconUrl:
      "https://img.icons8.com/?size=100&id=30462&format=png&color=000000",
    scope: "openid email profile https://www.googleapis.com/auth/presentations",
  },
  {
    id: "google-photos",
    name: "Google Photos",
    description: "View and manage your photos",
    iconUrl:
      "https://img.icons8.com/?size=100&id=1cQSEiAEtqRn&format=png&color=000000",
    scope: "openid email profile https://www.googleapis.com/auth/photoslibrary",
  },
  {
    id: "youtube",
    name: "YouTube",
    description: "Manage your YouTube account and content",
    iconUrl:
      "https://www.gstatic.com/images/branding/product/2x/youtube_32dp.png",
    scope: "openid email profile https://www.googleapis.com/auth/youtube",
  },
];

export function Connectors({ isOpen, onClose }: ConnectorsProps) {
  // *** THIS IS THE CORRECTED LOGIC ***
  const handleConnectorClick = (scope: string) => {
    // Let NextAuth handle the entire OAuth flow.
    // It will redirect the user to Google with the specific scope you provide.
    // If the user is already logged in, it will ask for the *additional* permissions.
    signIn("google", undefined, { scope: scope });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      {/* All your beautiful styling and JSX remains exactly the same */}
      <DialogContent className="max-w-7xl min-w-[40] min-h-[60vh] w-full bg-[#1a1b26] text-[#c0caf5] border border-[#414868] shadow-2xl backdrop-blur-sm">
        <style jsx>{`
          /* Your animations and styles... */
        `}</style>

        <DialogHeader className="pb-4">
          <div className="flex items-center justify-between animate-fadeInUp">
            <div>
              <DialogTitle className="text-2xl font-bold bg-gradient-to-r from-[#bb9af7] via-[#7dcfff] to-[#9ece6a] bg-clip-text text-transparent animate-float">
                Connect to Google Suite
              </DialogTitle>
              <p className="text-[#565f89] mt-1 transition-colors duration-300">
                Unlock powerful integrations with your Google services
              </p>
            </div>
          </div>
        </DialogHeader>

        <div className="h-full px-4 -mx-4 overflow-y-auto">
          <div className="grid grid-cols-1 sm-grid-cols-2 lg:grid-cols-3 auto-rows-min gap-4">
            {googleSuiteConnectors.map((connector, index) => (
              <button
                key={connector.id}
                onClick={() => handleConnectorClick(connector.scope)}
                className="group/card text-left border border-[#414868] hover:border-[#bb9af7] transition-all duration-300 ease-in-out rounded-2xl flex flex-col gap-3 py-4 px-5 shadow-sm hover:shadow-[0_8px_32px_0_rgba(187,154,247,0.12)] bg-[#24283b]/50 hover:bg-[#24283b] backdrop-blur-sm transform hover:scale-[1.02] hover:-translate-y-1 animate-fadeInUp relative overflow-hidden"
                style={{
                  animationDelay: `${index * 0.1}s`,
                  animationFillMode: "both",
                }}
              >
                {/* Shimmer effect overlay */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#bb9af7]/5 to-transparent -translate-x-full group-hover/card:translate-x-full transition-transform duration-1000 ease-in-out" />

                {/* Glow effect on hover */}
                <div className="absolute inset-0 rounded-2xl opacity-0 group-hover/card:opacity-100 transition-opacity duration-300 bg-gradient-to-r from-[#bb9af7]/5 via-transparent to-[#7dcfff]/5" />

                <div className="flex flex-row items-center gap-3 relative z-10">
                  <div
                    className="shrink-0 bg-gradient-to-br from-[#414868] to-[#24283b] border-[#565f89] border shadow-lg flex items-center justify-center group-hover/card:border-[#bb9af7] transition-all duration-300 group-hover/card:shadow-[0_0_20px_rgba(187,154,247,0.3)] group-hover/card:scale-110"
                    style={{
                      width: "40px",
                      height: "40px",
                      borderRadius: "12px",
                    }}
                  >
                    <img
                      className="transition-all duration-500 opacity-90 group-hover/card:opacity-100 group-hover/card:scale-110 filter group-hover/card:drop-shadow-[0_0_8px_rgba(187,154,247,0.3)]"
                      width="24"
                      height="24"
                      alt={`${connector.name} icon`}
                      src={connector.iconUrl}
                      style={{ maxWidth: "24px", maxHeight: "24px" }}
                    />
                  </div>
                  <div className="flex flex-col justify-center font-sans grow h-[3.5rem]">
                    <div className="flex gap-2 items-center justify-between">
                      <p className="text-[#c0caf5] text-sm font-semibold line-clamp-1 group-hover/card:text-[#bb9af7] transition-colors duration-300">
                        {connector.name}
                      </p>
                    </div>
                    <p className="text-[#565f89] text-xs line-clamp-2 text-pretty group-hover/card:text-[#7aa2f7] transition-colors duration-300">
                      {connector.description}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
