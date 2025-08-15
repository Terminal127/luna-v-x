"use client";

import {
  Calendar,
  Home,
  Inbox,
  Search,
  Settings,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  User2,
} from "lucide-react";

import { useSession } from "next-auth/react";
import { useState } from "react";

import {
  Sidebar,
  SidebarHeader,
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
import SettingsModal from "@/components/SettingsModal"; // Import the separate component

export function ChatSidebar() {
  const { data: session } = useSession();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Menu items with updated Settings handler
  const items = [
    {
      title: "Home",
      url: "/",
      icon: Home,
      onClick: null,
    },
    {
      title: "New Chat",
      url: "/chat",
      icon: MessageSquare,
      onClick: null,
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

          {/* Workspace Selector */}
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
