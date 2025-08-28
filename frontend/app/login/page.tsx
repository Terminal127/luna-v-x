"use client";

import React, { useEffect, useState } from "react";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  IconBrandGithub,
  IconBrandGoogle,
  IconChevronDown,
  IconSparkles,
} from "@tabler/icons-react";
import { motion, AnimatePresence } from "framer-motion";
import { TypeAnimation } from "react-type-animation"; // ⭐ 1. IMPORT TYPE ANIMATION

// New, more impressive examples with a "thinking" stream
const lunaExamples = [
  {
    id: 1,
    query: "Find the top 3 trending AI repositories on GitHub right now.",
    thoughts: [
      "Analyzing request...",
      "Connecting to GitHub API...",
      "Querying for repositories tagged 'AI'...",
      "Sorting by recent star count...",
      "Compiling results...",
    ],
    response:
      "I've found the top 3 trending AI repos. The leading one is 'SuperAGI' with a 32% increase in stars this week.",
    category: "Real-time Data Analysis",
  },
  {
    id: 2,
    query:
      "What's the overall sentiment about the new 'Dune: Part Two' movie on Twitter?",
    thoughts: [
      "Parsing social media intent...",
      "Connecting to Twitter/X API...",
      "Filtering for 'Dune Part Two' mentions...",
      "Running sentiment analysis model...",
      "Aggregating scores...",
    ],
    response:
      "Sentiment is overwhelmingly positive (92%), with audiences praising the cinematography and sound design.",
    category: "Public Sentiment Analysis",
  },
  {
    id: 3,
    query: "Compare the Q1 earnings reports for NVIDIA and AMD.",
    thoughts: [
      "Accessing financial databases...",
      "Locating SEC filings for NVDA & AMD...",
      "Extracting key financial metrics...",
      "Comparing revenue and profit margins...",
      "Generating summary...",
    ],
    response:
      "NVIDIA reported a 265% YoY revenue increase, significantly outpacing AMD's growth in the data center segment.",
    category: "Financial Intelligence",
  },
];

export default function LoginPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [currentExample, setCurrentExample] = useState(0);
  const [showThinking, setShowThinking] = useState(false);
  const [showResponse, setShowResponse] = useState(false);

  // Redirect authenticated users
  useEffect(() => {
    if (status === "authenticated") {
      router.push("/chat");
    }
  }, [status, router]);

  // Main animation sequence for the right panel
  useEffect(() => {
    const sequence = () => {
      setShowThinking(false);
      setShowResponse(false);

      // After a brief pause, start showing the "thinking" stream
      setTimeout(() => {
        setShowThinking(true);
      }, 1500); // Wait 1.5s after the user query types out

      // After the "thinking" is done, show the final response
      setTimeout(() => {
        setShowResponse(true);
      }, 3500); // thinking stream lasts for 2s
    };

    // Trigger the sequence when the example changes
    sequence();

    const interval = setInterval(() => {
      setCurrentExample((prev) => (prev + 1) % lunaExamples.length);
    }, 8000); // Rotate every 8 seconds to give user time to read

    return () => clearInterval(interval);
  }, [currentExample]);

  if (status === "loading" || status === "authenticated") {
    return (
      <main className="min-h-screen bg-[#1a1b26] flex items-center justify-center">
        <div className="text-[#c0caf5]">Loading...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen w-full bg-[#1a1b26] overflow-hidden">
      <div className="absolute inset-0 z-0 opacity-40">
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_800px_at_10%_20%,rgba(122,162,247,0.2),transparent)]"></div>
        <div className="absolute bottom-0 right-0 w-full h-full bg-[radial-gradient(circle_800px_at_90%_80%,rgba(187,154,247,0.2),transparent)]"></div>
      </div>

      <div className="container mx-auto px-4 lg:px-8 max-w-screen-2xl relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 min-h-screen items-center">
          {/* Left Section - Login Form */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.25, 1, 0.5, 1] }}
            className="flex items-center justify-center py-12"
          >
            <div className="w-full max-w-md">
              <div className="mb-8">
                <div className="flex items-center mb-6">
                  <div className="w-10 h-10 bg-gradient-to-br from-[#7aa2f7] to-[#bb9af7] rounded-lg flex items-center justify-center mr-4 shadow-lg shadow-[#bb9af7]/20">
                    <IconSparkles className="text-white h-6 w-6" />
                  </div>
                  <span className="text-2xl font-bold text-[#c0caf5]">
                    Luna
                  </span>
                </div>
                <h1 className="text-4xl lg:text-5xl font-bold text-[#c0caf5] mb-2 leading-tight">
                  Automate the impossible.
                </h1>
                <p className="text-lg text-[#a9b1d6]">
                  Give Luna a goal, and it will control the browser to achieve
                  it.
                </p>
              </div>

              {/* Your form and buttons are great, no changes needed here */}
              <div className="space-y-3 mb-6">
                <SocialButton
                  onClick={() => signIn("google", { callbackUrl: "/chat" })}
                >
                  <IconBrandGoogle className="w-5 h-5 mr-3" />
                  Continue with Google
                </SocialButton>
                <SocialButton
                  onClick={() => signIn("github", { callbackUrl: "/chat" })}
                >
                  <IconBrandGithub className="w-5 h-5 mr-3" />
                  Continue with GitHub
                </SocialButton>
              </div>
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#3b4261]" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-[#1a1b26] text-[#565f89]">OR</span>
                </div>
              </div>
              <form onSubmit={(e) => e.preventDefault()} className="space-y-4">
                <div>
                  <Label
                    htmlFor="email"
                    className="block text-sm font-medium text-[#7aa2f7] mb-2"
                  >
                    Continue with your email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@company.com"
                    className="w-full px-4 py-3 border border-[#3b4261] bg-[#24283b] text-[#c0caf5] placeholder-[#565f89] rounded-lg focus:ring-2 focus:ring-[#7aa2f7] focus:border-transparent transition-shadow"
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="w-full bg-gradient-to-r from-[#7aa2f7] to-[#82aaff] text-[#1a1b26] py-3 px-4 rounded-lg font-bold hover:opacity-90 transition-opacity shadow-lg shadow-[#7aa2f7]/20"
                >
                  Continue
                </button>
              </form>
            </div>
          </motion.div>

          {/* Right Section - Animated Chat Examples */}
          <div className="hidden lg:flex items-center justify-center p-8">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                duration: 0.8,
                delay: 0.2,
                ease: [0.25, 1, 0.5, 1],
              }}
              className="w-full max-w-2xl"
            >
              <div className="relative">
                {/* Glowing Effect */}
                <div className="absolute -inset-2 bg-gradient-to-br from-[#7aa2f7] to-[#bb9af7] rounded-3xl blur-xl opacity-20 group-hover:opacity-40 transition-opacity duration-500"></div>
                <div className="relative bg-[#24283b]/80 backdrop-blur-xl border border-[#414868]/50 rounded-2xl shadow-2xl p-6 min-h-[450px] flex flex-col">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={currentExample}
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -15 }}
                      transition={{ duration: 0.5, ease: "easeInOut" }}
                      className="flex-1 flex flex-col justify-end space-y-4"
                    >
                      {/* User Message */}
                      <div className="flex justify-end">
                        <div className="bg-[#7aa2f7] text-white rounded-lg px-4 py-3 max-w-sm">
                          <div className="text-sm font-medium">
                            {/* ⭐ 2. LIVE TYPING EFFECT */}
                            <TypeAnimation
                              key={currentExample}
                              sequence={[
                                lunaExamples[currentExample].query,
                                5000,
                              ]}
                              wrapper="span"
                              speed={70}
                              cursor={true}
                              repeat={0}
                            />
                          </div>
                        </div>
                      </div>

                      {/* ⭐ 3. AGENT "THINKING" STREAM */}
                      <AnimatePresence>
                        {showThinking && (
                          <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.3 }}
                            className="flex justify-start"
                          >
                            <div className="bg-[#2f3349] border border-[#3b4261] rounded-lg px-4 py-3 max-w-sm">
                              <div className="flex items-center gap-2 text-xs text-[#a9b1d6] italic">
                                <div className="w-2 h-2 bg-[#f7768e] rounded-full animate-pulse"></div>
                                <TypeAnimation
                                  key={`${currentExample}-thinking`}
                                  sequence={lunaExamples[
                                    currentExample
                                  ].thoughts.flatMap((t) => [t, 250])}
                                  wrapper="span"
                                  speed={80}
                                  cursor={false}
                                  repeat={0}
                                />
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Luna Response */}
                      <AnimatePresence>
                        {showResponse && (
                          <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: 0.2 }}
                            className="flex justify-start"
                          >
                            <div className="bg-[#2f3349] border border-[#3b4261] rounded-lg px-4 py-3 max-w-sm">
                              <div className="text-xs text-[#bb9af7] font-semibold mb-2">
                                {lunaExamples[currentExample].category}
                              </div>
                              <div className="text-sm text-[#c0caf5]">
                                {lunaExamples[currentExample].response}
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </main>
  );
}

// Helper component for social buttons - unchanged
const SocialButton = ({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick?: () => void;
}) => (
  <button
    onClick={onClick}
    className="w-full flex items-center justify-center px-4 py-3 border border-[#3b4261] bg-[#24283b] rounded-lg hover:bg-[#2f3349] hover:border-[#7aa2f7] transition-all duration-300 text-[#c0caf5] group"
  >
    <div className="flex items-center justify-center gap-3">{children}</div>
  </button>
);
