"use client";

import { DrawableAnimation } from "@/components/ui/DrawableAnimation";
import React, { useState, useEffect } from "react";
import { BackgroundBeams } from "../components/ui/background-beams";
import { FloatingDock } from "../components/ui/floating-dock";
import { Timeline } from "@/components/ui/timeline";
import { cn } from "@/lib/utils";

import {
  IconBrandGithub,
  IconBrandX,
  IconExchange,
  IconHome,
  IconUserScan,
  IconMessageCircle,
} from "@tabler/icons-react";

/* ---------------- TIMELINE DEMO ---------------- */
export function TimelineDemo() {
  const data = [
    {
      title: "2024",
      content: (
        <div>
          <p className="mb-8 text-xs font-normal text-neutral-800 md:text-sm dark:text-neutral-200">
            Built and launched Aceternity UI and Aceternity UI Pro from scratch
          </p>
          <div className="grid grid-cols-2 gap-4">
            {[
              "startup-1.webp",
              "startup-2.webp",
              "startup-3.webp",
              "startup-4.webp",
            ].map((img, idx) => (
              <img
                key={idx}
                src={`https://assets.aceternity.com/templates/${img}`}
                alt="startup template"
                width={500}
                height={500}
                className="h-20 w-full rounded-lg object-cover shadow-[0_0_24px_rgba(34,_42,_53,_0.06),_0_1px_1px_rgba(0,_0,_0,_0.05),_0_0_0_1px_rgba(34,_42,_53,_0.04),_0_0_4px_rgba(34,_42,_53,_0.08),_0_16px_68px_rgba(47,_48,_55,_0.05),_0_1px_0_rgba(255,_255,_255,_0.1)_inset] md:h-44 lg:h-60"
              />
            ))}
          </div>
        </div>
      ),
    },
    {
      title: "Early 2023",
      content: (
        <div>
          <p className="mb-8 text-xs font-normal text-neutral-800 md:text-sm dark:text-neutral-200">
            I usually run out of copy, but when I see content this big, I try to
            integrate lorem ipsum.
          </p>
          <p className="mb-8 text-xs font-normal text-neutral-800 md:text-sm dark:text-neutral-200">
            Lorem ipsum is for people who are too lazy to write copy. But we are
            not. Here are some more example of beautiful designs I built.
          </p>
          <div className="grid grid-cols-2 gap-4">
            {[
              "https://assets.aceternity.com/pro/hero-sections.png",
              "https://assets.aceternity.com/features-section.png",
              "https://assets.aceternity.com/pro/bento-grids.png",
              "https://assets.aceternity.com/cards.png",
            ].map((src, idx) => (
              <img
                key={idx}
                src={src}
                alt="design template"
                width={500}
                height={500}
                className="h-20 w-full rounded-lg object-cover shadow-[0_0_24px_rgba(34,_42,_53,_0.06),_0_1px_1px_rgba(0,_0,_0,_0.05),_0_0_0_1px_rgba(34,_42,_53,_0.04),_0_0_4px_rgba(34,_42,_53,_0.08),_0_16px_68px_rgba(47,_48,_55,_0.05),_0_1px_0_rgba(255,_255,_255,_0.1)_inset] md:h-44 lg:h-60"
              />
            ))}
          </div>
        </div>
      ),
    },
    {
      title: "Changelog",
      content: (
        <div>
          <p className="mb-4 text-xs font-normal text-neutral-800 md:text-sm dark:text-neutral-200">
            Deployed 5 new components on Aceternity today
          </p>
          <div className="mb-8 space-y-2">
            {[
              "✅ Card grid component",
              "✅ Startup template Aceternity",
              "✅ Random file upload lol",
              "✅ Himesh Reshammiya Music CD",
              "✅ Salman Bhai Fan Club registrations open",
            ].map((item, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 text-xs text-neutral-700 md:text-sm dark:text-neutral-300"
              >
                {item}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              "https://assets.aceternity.com/pro/hero-sections.png",
              "https://assets.aceternity.com/features-section.png",
              "https://assets.aceternity.com/pro/bento-grids.png",
              "https://assets.aceternity.com/cards.png",
            ].map((src, idx) => (
              <img
                key={idx}
                src={src}
                alt="template"
                width={500}
                height={500}
                className="h-20 w-full rounded-lg object-cover shadow-[0_0_24px_rgba(34,_42,_53,_0.06),_0_1px_1px_rgba(0,_0,_0,_0.05),_0_0_0_1px_rgba(34,_42,_53,_0.04),_0_0_4px_rgba(34,_42,_53,_0.08),_0_16px_68px_rgba(47,_48,_55,_0.05),_0_1px_0_rgba(255,_255,_255,_0.1)_inset] md:h-44 lg:h-60"
              />
            ))}
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="relative w-full">
      <Timeline data={data} />
    </div>
  );
}

/* ---------------- FLOATING DOCK DEMO ---------------- */
export function FloatingDockDemo() {
  const links = [
    {
      title: "Home",
      icon: <IconHome className="h-full w-full text-[#c0caf5]" />,
      href: "/",
    },
    {
      title: "Chat",
      icon: <IconMessageCircle className="h-full w-full text-[#c0caf5]" />,
      href: "/chat",
    },
    {
      title: "login",
      icon: <IconUserScan className="h-full w-full text-[#c0caf5]" />,
      href: "/login",
    },
    {
      title: "Changelog",
      icon: <IconExchange className="h-full w-full text-[#c0caf5]" />,
      href: "/changelog",
    },
    {
      title: "Twitter",
      icon: <IconBrandX className="h-full w-full text-[#c0caf5]" />,
      href: "https://twitter.com/YOUR_TWITTER_HANDLE",
    },
    {
      title: "GitHub",
      icon: <IconBrandGithub className="h-full w-full text-[#c0caf5]" />,
      href: "https://github.com/Terminal127",
    },
  ];

  return (
    <FloatingDock
      items={links}
      mobileClassName="bg-[#1a1b26] border border-[#414868]"
      desktopClassName="bg-[#1a1b26] border border-[#414868] shadow-lg"
    />
  );
}

/* ---------------- MAIN PAGE COMPONENT ---------------- */
export default function Page() {
  const [isIntroVisible, setIsIntroVisible] = useState(true);

  useEffect(() => {
    // Hide the intro animation after a delay
    const timer = setTimeout(() => {
      setIsIntroVisible(false);
    }, 2000); // Adjust duration as needed

    return () => clearTimeout(timer);
  }, []);

  // Effect to control body scrolling
  useEffect(() => {
    if (isIntroVisible) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
    }
    // Cleanup function to restore scroll on component unmount
    return () => {
      document.body.style.overflow = "auto";
    };
  }, [isIntroVisible]);

  return (
    <div className="relative min-h-screen bg-[#1a1b26]">
      {/* 1. Intro Animation Overlay - Changed to `fixed` */}
      <div
        className={cn(
          "fixed inset-0 z-50 flex items-center justify-center bg-[#1a1b26] transition-opacity duration-1000",
          isIntroVisible ? "opacity-100" : "opacity-0 pointer-events-none", // Fade out and disable clicks
        )}
      >
        <div className="w-full max-w-2xl">
          <DrawableAnimation />
        </div>
      </div>

      {/* 2. Main Page Content - Fades in */}
      <div
        className={cn(
          "transition-opacity duration-1000",
          isIntroVisible ? "opacity-0" : "opacity-100",
        )}
      >
        {/* HERO SECTION */}
        <section className="relative h-screen flex flex-col items-center justify-center overflow-hidden">
          <div className="absolute top-12 left-1/2 transform -translate-x-1/2 z-50">
            <FloatingDockDemo />
          </div>
          <div className="max-w-3xl mx-auto p-10 text-center relative z-10">
            <h1 className="text-lg md:text-6xl lg:text-7xl bg-clip-text text-transparent bg-gradient-to-b from-[#c0caf5] to-[#7aa2f7] font-sans font-bold tracking-tight">
              Welcome to <span className="text-[#bb9af7]">Luna</span> — Version
              X
            </h1>
            <p className="text-[#a9b1d6] max-w-xl mx-auto my-6 text-base md:text-lg leading-relaxed">
              This time, it’s{" "}
              <span className="text-[#7dcfff] font-medium">Agentic</span>. No
              more rigid if-else chains — Luna adapts, decides, and acts. You
              don’t just give commands — you collaborate with a mind that sees
              the path ahead.
            </p>
          </div>
          <BackgroundBeams />
        </section>

        {/* TIMELINE SECTION */}
        <section className="relative z-10 w-full py-20 bg-[#1a1b26]">
          <TimelineDemo />
        </section>
      </div>
    </div>
  );
}
