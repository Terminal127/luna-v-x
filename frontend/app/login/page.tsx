"use client";

import React, { useEffect, useState } from "react";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  IconBrandGithub,
  IconBrandGoogle,
  IconSparkles,
} from "@tabler/icons-react";
import { motion, AnimatePresence } from "framer-motion";
import { TypeAnimation } from "react-type-animation";

// Your brilliant, eye-catching examples - unchanged
const lunaExamples = [
  {
    id: 1,
    query: "Find the top 3 trending AI repositories on GitHub right now.",
    thoughts: [
      "Analyzing request...",
      "Connecting to GitHub API...",
      "Querying repositories...",
      "Sorting results...",
      "Compiling summary...",
    ],
    response:
      "The leading repo is 'SuperAGI' with a 32% increase in stars this week.",
    category: "Real-time Data Analysis",
  },
  {
    id: 2,
    query: "What's the sentiment about the 'Dune: Part Two' movie on Twitter?",
    thoughts: [
      "Parsing social media intent...",
      "Connecting to Twitter/X API...",
      "Running sentiment analysis model...",
      "Aggregating scores...",
    ],
    response:
      "Sentiment is overwhelmingly positive (92%), praising the cinematography.",
    category: "Public Sentiment Analysis",
  },
  {
    id: 3,
    query: "Compare the Q1 earnings reports for NVIDIA and AMD.",
    thoughts: [
      "Accessing financial databases...",
      "Locating SEC filings...",
      "Extracting key metrics...",
      "Generating comparison...",
    ],
    response:
      "NVIDIA reported a 265% YoY revenue increase, outpacing AMD's growth.",
    category: "Financial Intelligence",
  },
];

export default function LoginPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [currentExample, setCurrentExample] = useState(0);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [showThinking, setShowThinking] = useState(false);
  const [showResponse, setShowResponse] = useState(false);

  useEffect(() => {
    if (status === "authenticated") {
      router.push("/chat");
    }
  }, [status, router]);

  useEffect(() => {
    const sequence = () => {
      setShowThinking(false);
      setShowResponse(false);
      setTimeout(() => setShowThinking(true), 1500);
      setTimeout(() => setShowResponse(true), 3500);
    };
    sequence();
    const interval = setInterval(() => {
      setCurrentExample((prev) => (prev + 1) % lunaExamples.length);
    }, 8000);
    return () => clearInterval(interval);
  }, [currentExample]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const result = await signIn("credentials", {
      redirect: false,
      email,
      password,
    });

    if (result?.error) {
      setError("Invalid email or password. Please try again.");
    } else if (result?.ok) {
      router.push("/chat");
    }
    setIsLoading(false);
  };

  if (status === "loading" || status === "authenticated") {
    return (
      <main className="h-screen w-full bg-[#1a1b26] flex items-center justify-center">
        <div className="text-[#c0caf5]">Loading...</div>
      </main>
    );
  }

  return (
    <main className="h-screen w-full bg-[#1a1b26] overflow-hidden">
      <div className="absolute inset-0 z-0 opacity-40">
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_800px_at_10%_20%,rgba(122,162,247,0.2),transparent)]"></div>
        <div className="absolute bottom-0 right-0 w-full h-full bg-[radial-gradient(circle_800px_at_90%_80%,rgba(187,154,247,0.2),transparent)]"></div>
      </div>

      <div className="container mx-auto px-4 lg:px-8 max-w-screen-2xl relative z-10 h-full">
        <div className="grid grid-cols-1 lg:grid-cols-2 h-full items-center">
          {/* ⭐ START: CORRECTED LEFT SECTION */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.25, 1, 0.5, 1] }}
            className="flex items-center justify-center"
          >
            <div className="w-full max-w-sm space-y-8">
              {/* Header */}
              <div className="text-center">
                <div className="flex items-center justify-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-gradient-to-br from-[#7aa2f7] to-[#bb9af7] rounded-lg flex items-center justify-center shadow-lg shadow-[#bb9af7]/20">
                    <IconSparkles className="text-white h-6 w-6" />
                  </div>
                  <span className="text-2xl font-bold text-[#c0caf5]">
                    Luna
                  </span>
                </div>
                <h1 className="text-4xl font-bold text-[#c0caf5] leading-tight">
                  Automate the impossible.
                </h1>
                <p className="text-md text-[#a9b1d6] mt-2">
                  Sign in to control the web with AI.
                </p>
              </div>

              {/* Social Buttons (Side-by-Side) */}
              <div className="flex items-center gap-4">
                <SocialButton
                  onClick={() => signIn("google", { callbackUrl: "/chat" })}
                >
                  <IconBrandGoogle className="w-5 h-5" />
                  Google
                </SocialButton>
                <SocialButton
                  onClick={() => signIn("github", { callbackUrl: "/chat" })}
                >
                  <IconBrandGithub className="w-5 h-5" />
                  GitHub
                </SocialButton>
              </div>

              {/* Divider */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#3b4261]" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-[#1a1b26] text-[#565f89]">OR</span>
                </div>
              </div>

              {/* Email Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-400 mb-1.5"
                  >
                    Email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-2.5 border border-[#3b4261] bg-[#24283b] text-[#c0caf5] placeholder-[#565f89] rounded-md focus:ring-2 focus:ring-[#7aa2f7] focus:border-transparent transition-shadow"
                    required
                  />
                </div>
                <div>
                  <Label
                    htmlFor="password"
                    className="block text-sm font-medium text-gray-400 mb-1.5"
                  >
                    Password
                  </Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-2.5 border border-[#3b4261] bg-[#24283b] text-[#c0caf5] placeholder-[#565f89] rounded-md focus:ring-2 focus:ring-[#7aa2f7] focus:border-transparent transition-shadow"
                    required
                  />
                </div>

                {error && (
                  <p className="text-sm text-red-400 text-center pt-1">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex justify-center items-center h-10 bg-[#c0caf5] text-[#1a1b26] font-bold rounded-md hover:bg-white transition-colors shadow-lg shadow-black/20 disabled:opacity-50"
                >
                  {isLoading ? "Signing In..." : "Sign In"}
                </button>
              </form>

              <div className="text-center">
                <p className="text-sm text-gray-500">
                  New to Luna?
                  <Link
                    href="/signup"
                    className="ml-1.5 font-semibold text-gray-300 hover:text-white hover:underline"
                  >
                    Create an account
                  </Link>
                </p>
              </div>
            </div>
          </motion.div>
          {/* ⭐ END: CORRECTED LEFT SECTION */}

          {/* Right Section - Animated Chat Examples (Unchanged but will look balanced now) */}
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
                      <div className="flex justify-end">
                        <div className="bg-[#7aa2f7] text-white rounded-lg px-4 py-3 max-w-sm">
                          <div className="text-sm font-medium">
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
    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-[#3b4261] bg-[#24283b] rounded-md hover:bg-[#2f3349] hover:border-[#7aa2f7] transition-all duration-300 text-[#c0caf5] group"
  >
    {children}
  </button>
);
