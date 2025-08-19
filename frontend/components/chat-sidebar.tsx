"use client";

import {
  Home,
  Settings,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  User2,
  BellDot,
  History, // Using History icon for session items
} from "lucide-react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

import { useSession } from "next-auth/react";
import { useState, useEffect, useCallback } from "react";

import {
  Sidebar,
  SidebarFooter,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";

import { signOut } from "next-auth/react";
import SettingsModal from "@/components/SettingsModal";

// --- INTERFACES & PROPS ---
const DEFAULT_TOOL_NAME = "default_tool";

// Represents a single session object received from the backend
interface UserSession {
  session_id: string;
  last_updated: string;
  message_count: number;
}

// Defines the props this component expects from its parent (ChatPage)
interface ChatSidebarProps {
  sessions: UserSession[];
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onCreateNewSession: () => void;
}

// The component now accepts the defined props
export function ChatSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateNewSession,
}: ChatSidebarProps) {
  const { data: session } = useSession();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [seenTools, setSeenTools] = useState<string[]>([]);

  // --- Tool Action Logic (remains unchanged) ---
  const fetchApiStatus = useCallback(async () => {
    try {
      const response = await fetch("http://localhost:9000/");
      if (!response.ok) {
        setActiveTool(null);
        return;
      }
      const data = await response.json();
      if (data.tool_name && data.tool_name !== DEFAULT_TOOL_NAME) {
        setActiveTool(data.tool_name);
      } else {
        setActiveTool(null);
      }
    } catch (error) {
      console.error("Failed to fetch from API on port 9000:", error);
      setActiveTool(null);
    }
  }, []);

  useEffect(() => {
    fetchApiStatus();
    const intervalId = setInterval(fetchApiStatus, 5000);
    return () => clearInterval(intervalId);
  }, [fetchApiStatus]);

  const updateAndResetApi = async (status: "A" | "D") => {
    try {
      const requestBody = {
        authorization: status,
        tool_name: "default_tool",
        tool_args: {},
      };
      await fetch("http://localhost:9000/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      return true;
    } catch (error) {
      console.error("Failed to update API state:", error);
      return false;
    }
  };

  const handleAction = async (toolName: string, status: "A" | "D") => {
    const success = await updateAndResetApi(status);
    if (success) {
      setSeenTools([]);
      await fetchApiStatus();
    }
  };

  // --- Sidebar Items ---
  // The "New Chat" button's onClick is now wired to the prop function
  const items = [
    { title: "Home", url: "/", icon: Home, onClick: null },
    {
      title: "New Chat",
      url: "#",
      icon: MessageSquare,
      onClick: onCreateNewSession,
    },
    {
      title: "Settings",
      url: "#",
      icon: Settings,
      onClick: () => setIsSettingsOpen(true),
    },
  ];

  const handleItemClick = (item: (typeof items)[0], e: React.MouseEvent) => {
    if (item.onClick) {
      e.preventDefault();
      item.onClick();
    }
  };

  const isToolNotificationVisible =
    activeTool && !seenTools.includes(activeTool);

  return (
    <>
      <Sidebar side="left" variant="floating" collapsible="offcanvas">
        <SidebarContent>
          {/* --- Application Group --- */}
          <SidebarGroup>
            <SidebarGroupLabel />
            <SidebarGroupLabel />
            <SidebarGroupLabel>Application</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {items.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild>
                      <a
                        href={item.url}
                        onClick={(e) => handleItemClick(item, e)}
                      >
                        <item.icon />
                        <span>{item.title}</span>
                      </a>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          {/* --- Action Required Group (Unchanged) --- */}
          {isToolNotificationVisible && (
            <SidebarGroup>
              <SidebarGroupLabel>Action Required</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <div className="flex items-center w-full group transition-all duration-300">
                      <SidebarMenuButton className="flex-grow justify-start text-yellow-400 hover:text-yellow-300">
                        <BellDot size={18} />
                        <span className="font-semibold">{activeTool}</span>
                      </SidebarMenuButton>
                      <div className="flex items-center ml-2 space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => handleAction(activeTool!, "A")}
                          className="text-xs text-white font-semibold bg-green-600 hover:bg-green-500 rounded px-2 py-1 transition-colors"
                          title={`Approve ${activeTool}`}
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleAction(activeTool!, "D")}
                          className="text-xs text-white font-semibold bg-red-600 hover:bg-red-500 rounded px-2 py-1 transition-colors"
                          title={`Deny ${activeTool}`}
                        >
                          Deny
                        </button>
                      </div>
                    </div>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )}

          {/* --- Dynamic Session History Group --- */}
          <Collapsible defaultOpen className="group/collapsible">
            <SidebarGroup>
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  Session History
                  <ChevronDown className="ml-auto transition-transform group-data-[state=open]/collapsible:rotate-180" />
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {sessions.length > 0 ? (
                      sessions.map((sess) => (
                        <SidebarMenuItem key={sess.session_id}>
                          <SidebarMenuButton
                            onClick={() => onSelectSession(sess.session_id)}
                            // Highlight the button if it's the active session
                            className={
                              sess.session_id === activeSessionId
                                ? "bg-gray-700/50 text-white font-semibold"
                                : ""
                            }
                          >
                            <History size={16} className="flex-shrink-0" />
                            {/* Truncate long text and format the date */}
                            <span className="truncate flex-1 text-left">
                              Chat from{" "}
                              {new Date(sess.last_updated).toLocaleString(
                                undefined,
                                {
                                  month: "short",
                                  day: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                },
                              )}
                            </span>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      ))
                    ) : (
                      <SidebarMenuItem>
                        <span className="text-xs text-gray-500 px-4 py-2 italic">
                          No past sessions found
                        </span>
                      </SidebarMenuItem>
                    )}
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </SidebarGroup>
          </Collapsible>
        </SidebarContent>

        {/* --- User Menu in Footer (Unchanged) --- */}
        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <SidebarMenuButton>
                    <div className="flex items-center gap-2">
                      <div className="relative">
                        {session?.user?.image ? (
                          <img
                            src={session.user.image}
                            alt={session.user?.name || "User"}
                            className="w-6 h-6 rounded-full object-cover"
                          />
                        ) : (
                          <User2 className="w-6 h-6" />
                        )}
                      </div>
                      <span>{session?.user?.name || "User"}</span>
                    </div>
                    <ChevronUp className="ml-auto" />
                  </SidebarMenuButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  side="top"
                  className="w-[--radix-popper-anchor-width]"
                >
                  <DropdownMenuItem>
                    <span>Account</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <span>Billing</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => signOut({ callbackUrl: "/" })}
                  >
                    <span>Sign out</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </>
  );
}
