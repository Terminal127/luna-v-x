"use client";
import { Connectors } from "@/components/Connectors";
import { AuthorizationModal } from "@/components/AuthorizationModal"; // Ensure this path is correct for your project
import { toast } from "sonner";

import {
  Home,
  Settings,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  User2,
  History,
  MoreHorizontal, // Icon for the "three dots" menu
} from "lucide-react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

import { useSession } from "next-auth/react";
import { useState, useEffect, useCallback, useRef } from "react";

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
const AUTH_API_URL = process.env.NEXT_PUBLIC_TOOL_API_BASE_URL;
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

interface UserSession {
  session_id: string;
  last_updated: string;
  message_count: number;
}

interface ChatSidebarProps {
  sessions: UserSession[];
  setSessions: React.Dispatch<React.SetStateAction<UserSession[]>>; // Required to update the list after deletion
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onCreateNewSession: () => void;
}

interface AuthRequest {
  session_id: string;
  tool_name: string;
  tool_args: Record<string, any>;
}

export function ChatSidebar({
  sessions,
  setSessions,
  activeSessionId,
  onSelectSession,
  onCreateNewSession,
}: ChatSidebarProps) {
  const { data: session } = useSession();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isConnectorsOpen, setIsConnectorsOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authRequest, setAuthRequest] = useState<AuthRequest | null>(null);

  // BUG FIX: Refs to prevent polling race conditions and repeat notifications
  const isResponding = useRef(false);
  const notifiedRequests = useRef(new Set());

  const pollForAuthRequest = useCallback(async () => {
    // Pause polling if the modal is open, a response is being sent, or there's no active session
    if (
      !AUTH_API_URL ||
      isAuthModalOpen ||
      !activeSessionId ||
      isResponding.current
    )
      return;

    try {
      const response = await fetch(`${AUTH_API_URL}/${activeSessionId}`);
      if (!response.ok) return;

      const data: AuthRequest = await response.json();

      // If a request exists and we haven't already shown a toast for it...
      if (
        data &&
        data.tool_name &&
        !notifiedRequests.current.has(data.session_id)
      ) {
        notifiedRequests.current.add(data.session_id); // Mark as notified to prevent toast spam
        toast.warning("Authorization Required", {
          description: `The AI needs permission to use the '${data.tool_name}' tool.`,
          action: {
            label: "Review",
            onClick: () => {
              setAuthRequest(data);
              setIsAuthModalOpen(true);
            },
          },
          duration: 120000, // Stay for 2 minutes or until dismissed
        });
      }
    } catch (error) {
      console.error(`Failed to fetch auth status:`, error);
    }
  }, [activeSessionId, isAuthModalOpen]);

  useEffect(() => {
    const intervalId = setInterval(pollForAuthRequest, 2500); // Poll every 2.5 seconds
    return () => clearInterval(intervalId);
  }, [pollForAuthRequest]);

  const handleAuthResponse = async (
    authorization: "A" | "D",
    modifiedArgs?: Record<string, any>,
  ) => {
    if (!AUTH_API_URL || !authRequest) return;

    // BUG FIX: Immediately pause polling
    isResponding.current = true;
    setIsAuthModalOpen(false);

    try {
      await fetch(`${AUTH_API_URL}/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: authRequest.session_id,
          authorization,
          tool_args: modifiedArgs,
        }),
      });
    } catch (error) {
      console.error("Failed to submit auth response:", error);
      toast.error("Failed to send authorization response.");
    } finally {
      // After a delay, reset state and resume polling
      setTimeout(() => {
        notifiedRequests.current.delete(authRequest.session_id);
        setAuthRequest(null);
        isResponding.current = false;
      }, 3000); // Wait 3 seconds for the backend to process the response
    }
  };

  const handleDeleteSession = async (sessionIdToDelete: string) => {
    if (!session?.user?.email) {
      toast.error("Could not delete: User email not found.");
      return;
    }

    const previousSessions = sessions;
    setSessions((currentSessions) =>
      currentSessions.filter((s) => s.session_id !== sessionIdToDelete),
    );

    try {
      const encodedEmail = encodeURIComponent(session.user.email);
      const response = await fetch(
        `${API_BASE_URL}/api/session/${sessionIdToDelete}?email=${encodedEmail}`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      toast.success("Session deleted.");

      if (activeSessionId === sessionIdToDelete) {
        onCreateNewSession();
      }
    } catch (error) {
      console.error("Deletion error:", error);
      toast.error("Failed to delete session. Restoring list.");
      setSessions(previousSessions); // Rollback on failure
    }
  };

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

  return (
    <>
      <Sidebar side="left" variant="floating" collapsible="offcanvas">
        <SidebarContent>
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
                        <SidebarMenuItem
                          key={sess.session_id}
                          className="relative group/item"
                        >
                          <SidebarMenuButton
                            onClick={() => onSelectSession(sess.session_id)}
                            className={`w-full ${sess.session_id === activeSessionId ? "bg-gray-700/50 text-white font-semibold" : ""}`}
                          >
                            <History size={16} className="flex-shrink-0" />
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
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md opacity-0 group-hover/item:opacity-100 hover:bg-gray-700 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 transition-opacity">
                                <MoreHorizontal size={16} />
                              </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent side="right">
                              <DropdownMenuItem
                                className="text-red-500 focus:text-red-400 focus:bg-red-900/50 cursor-pointer"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteSession(sess.session_id);
                                }}
                              >
                                Delete Chat
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
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
                  <DropdownMenuItem onClick={() => setIsConnectorsOpen(true)}>
                    <span>Connectors</span>
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
      <Connectors
        isOpen={isConnectorsOpen}
        onClose={() => setIsConnectorsOpen(false)}
      />

      <AuthorizationModal
        isOpen={isAuthModalOpen}
        onClose={() => handleAuthResponse("D")}
        authRequest={authRequest}
        onSubmit={handleAuthResponse}
      />
    </>
  );
}
