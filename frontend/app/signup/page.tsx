// app/signup/page.tsx (This code is correct and needs no changes)

"use client";

import React, { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { IconSparkles } from "@tabler/icons-react";
import { motion } from "framer-motion";
import { toast } from "sonner";

export default function SignUpPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      // This fetch call works perfectly with the new Route Handler
      const response = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || "Something went wrong!");
      }

      toast.success("Account created! Signing you in...");

      const result = await signIn("credentials", {
        redirect: false,
        email,
        password,
      });

      if (result?.error) {
        toast.error(result.error);
        setIsLoading(false);
      } else {
        router.push("/chat");
      }
    } catch (err: any) {
      toast.error(err.message);
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen w-full bg-[#1a1b26] flex items-center justify-center p-4 overflow-hidden">
      <div className="absolute top-0 left-0 -translate-x-1/4 translate-y-1/4 w-[800px] h-[800px] bg-gradient-to-tr from-[#7aa2f7]/20 to-[#1a1b26] rounded-full blur-3xl opacity-50"></div>
      <div className="absolute bottom-0 right-0 translate-x-1/4 -translate-y-1/4 w-[800px] h-[800px] bg-gradient-to-tr from-[#bb9af7]/20 to-[#1a1b26] rounded-full blur-3xl opacity-50"></div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeInOut" }}
        className="w-full max-w-md bg-[#24283b]/60 backdrop-blur-md border border-[#414868]/50 rounded-2xl shadow-xl p-8 relative z-10"
      >
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <div className="w-10 h-10 bg-gradient-to-br from-[#7aa2f7] to-[#bb9af7] rounded-lg flex items-center justify-center mr-4 shadow-lg shadow-[#bb9af7]/20">
              <IconSparkles className="text-white h-6 w-6" />
            </div>
            <span className="text-2xl font-bold text-[#c0caf5]">Luna</span>
          </div>
          <h1 className="text-3xl font-bold text-[#c0caf5]">
            Create Your Account
          </h1>
          <p className="text-md text-[#a9b1d6] mt-2">
            Join the future of browsing.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <Label
              htmlFor="email"
              className="block text-sm font-medium text-[#7aa2f7] mb-2"
            >
              Email Address
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 border border-[#3b4261] bg-[#24283b] text-[#c0caf5] placeholder-[#565f89] rounded-lg focus:ring-2 focus:ring-[#7aa2f7] focus:border-transparent transition-shadow"
            />
          </div>

          <div>
            <Label
              htmlFor="password"
              className="block text-sm font-medium text-[#7aa2f7] mb-2"
            >
              Password
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="8+ characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 border border-[#3b4261] bg-[#24283b] text-[#c0caf5] placeholder-[#565f89] rounded-lg focus:ring-2 focus:ring-[#7aa2f7] focus:border-transparent transition-shadow"
            />
          </div>

          <div>
            <Label
              htmlFor="confirmPassword"
              className="block text-sm font-medium text-[#7aa2f7] mb-2"
            >
              Confirm Password
            </Label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="Re-enter your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full px-4 py-3 border border-[#3b4261] bg-[#24283b] text-[#c0caf5] placeholder-[#565f89] rounded-lg focus:ring-2 focus:ring-[#7aa2f7] focus:border-transparent transition-shadow"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex justify-center items-center h-11 px-4 bg-gradient-to-r from-[#7aa2f7] to-[#82aaff] text-[#1a1b26] font-bold rounded-lg hover:opacity-90 transition-opacity shadow-lg shadow-[#7aa2f7]/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        <div className="mt-8 text-center">
          <p className="text-sm text-gray-500">
            Already have an account?
            <Link
              href="/login"
              className="ml-2 font-semibold text-gray-300 hover:text-white hover:underline"
            >
              Sign In
            </Link>
          </p>
        </div>
      </motion.div>
    </main>
  );
}
