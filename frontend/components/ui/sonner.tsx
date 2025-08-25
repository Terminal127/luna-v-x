"use client";

import { useTheme } from "next-themes";
import { Toaster as Sonner, ToasterProps } from "sonner";

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      // This simple style block applies a unified Tokyonight theme
      // to all toasts by setting the CSS variables that Sonner uses.
      style={
        {
          "--normal-bg": "#24283b", // Tokyonight Background
          "--normal-text": "#c0caf5", // Tokyonight Foreground
          "--normal-border": "#414868", // Tokyonight Border Color
          "--action-bg": "#7aa2f7", // Tokyonight Blue (for buttons)
          "--action-text": "#1a1b26", // Dark text for button contrast
          "--cancel-bg": "#565f89", // A muted Tokyonight color
          "--cancel-text": "#c0caf5",
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
