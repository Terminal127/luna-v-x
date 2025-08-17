"use client";

import {
  Home,
  Settings,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  User2,
  BellDot,
} from "lucide-react";

import { useSession } from "next-auth/react";
import { useState, useEffect, useCallback } from "react"; // ✅ Import useCallback

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

const DEFAULT_TOOL_NAME = "default_tool";

export function ChatSidebar() {
  const { data: session } = useSession();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [seenTools, setSeenTools] = useState<string[]>([]);

  // ✅ 1. The API fetching logic is now in a memoized function.
  // This allows us to call it from multiple places without re-creating it.
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
  }, []); // Empty dependency array as it has no external dependencies.

  // ✅ 2. The useEffect hook is now simpler. It calls the fetch function.
  useEffect(() => {
    fetchApiStatus(); // Fetch on initial load
    const intervalId = setInterval(fetchApiStatus, 5000); // Poll every 5 seconds
    return () => clearInterval(intervalId);
  }, [fetchApiStatus]); // Depend on the memoized function.

  const updateAndResetApi = async (status: "A" | "D") => {
    try {
      const requestBody = {
        authorization: status,
        tool_name: "default_tool",
        tool_args: {},
      };
      const response = await fetch("http://localhost:9000/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }
      return true; // Return true on success
    } catch (error) {
      console.error("Failed to update API state:", error);
      return false; // Return false on failure
    }
  };

  // ✅ 3. The handlers are now async to await the API call.
  const handleAction = async (toolName: string, status: "A" | "D") => {
    const success = await updateAndResetApi(status);
    if (success) {
      // Upon success, clear the list of seen tools to refresh the state.
      // Any new tool that was set on the server will now appear.
      setSeenTools([]);
      // Immediately fetch the new status from the server.
      await fetchApiStatus();
    }
  };

  const items = [
    { title: "Home", url: "/", icon: Home, onClick: null },
    { title: "New Chat", url: "/chat", icon: MessageSquare, onClick: null },
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
          {/* ... your existing Application group and Workspace Selector ... */}
          <SidebarGroup>
            <SidebarGroupLabel></SidebarGroupLabel>
            <SidebarGroupLabel></SidebarGroupLabel>
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

          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <SidebarMenuButton>
                    Select Workspace
                    <ChevronDown className="ml-auto" />
                  </SidebarMenuButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-[--radix-popper-anchor-width]">
                  <DropdownMenuItem>
                    <span>Acme Inc</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <span>Acme Corp.</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarContent>

        {/* User Menu in Footer */}
        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <SidebarMenuButton>
                    <div className="flex items-center gap-2">
                      <div className="relative">
                        {session?.user?.image ? (
                          <>
                            <img
                              src={session.user.image}
                              alt={session.user?.name || "User"}
                              className="w-6 h-6 rounded-full object-cover"
                              onError={(e) => {
                                console.log(
                                  "Image failed to load:",
                                  session.user?.image,
                                );
                                const target = e.currentTarget;
                                target.style.display = "none";
                                // Show fallback icon
                                const fallback =
                                  target.nextElementSibling as HTMLElement;
                                if (fallback) fallback.style.display = "block";
                              }}
                              onLoad={() => {
                                console.log(
                                  "Image loaded successfully:",
                                  session.user?.image,
                                );
                              }}
                            />
                            <User2 className="w-6 h-6 hidden" />
                          </>
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

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </>
  );
}
