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
  IconChevronDown,
  IconCheck,
  IconArrowRight,
} from "@tabler/icons-react";

// Luna capabilities showcase
const lunaCapabilities = [
  {
    id: 1,
    title: "Smart Web Browsing",
    description:
      "Navigate and extract data from any website with intelligent parsing",
    features: [
      "Real-time data extraction",
      "JavaScript rendering",
      "Anti-detection browsing",
    ],
    icon: "🌐",
  },
  {
    id: 2,
    title: "Social Media Intelligence",
    description: "Monitor and analyze social platforms for trends and insights",
    features: [
      "Twitter trend analysis",
      "Reddit sentiment mining",
      "LinkedIn lead generation",
    ],
    icon: "📱",
  },
  {
    id: 3,
    title: "Content Aggregation",
    description:
      "Curate and organize content from multiple sources automatically",
    features: [
      "YouTube video curation",
      "News article summarization",
      "Research compilation",
    ],
    icon: "📊",
  },
  {
    id: 4,
    title: "Business Intelligence",
    description: "Gather competitive insights and market research efficiently",
    features: [
      "Competitor analysis",
      "Pricing intelligence",
      "Market trend tracking",
    ],
    icon: "💼",
  },
];

const pricingPlans = [
  {
    name: "Starter",
    price: "Free",
    period: "forever",
    description: "Perfect for trying out Luna's capabilities",
    features: [
      "100 browsing requests/month",
      "Basic web scraping",
      "Email support",
      "Community access",
    ],
    highlighted: false,
  },
  {
    name: "Professional",
    price: "$29",
    period: "per month",
    description: "For professionals and growing businesses",
    features: [
      "5,000 browsing requests/month",
      "Advanced AI analysis",
      "Priority support",
      "API access",
      "Custom integrations",
      "Advanced analytics",
    ],
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "pricing",
    description: "For large teams and organizations",
    features: [
      "Unlimited requests",
      "Dedicated infrastructure",
      "24/7 phone support",
      "Custom deployment",
      "SLA guarantee",
      "Advanced security",
    ],
    highlighted: false,
  },
];

export default function SignupPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [currentCapability, setCurrentCapability] = useState(0);
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    password: "",
    company: "",
  });

  // Redirect authenticated users to chat
  useEffect(() => {
    if (status === "authenticated") {
      router.push("/chat");
    }
  }, [status, router]);

  // Auto-rotate capabilities
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentCapability((prev) => (prev + 1) % lunaCapabilities.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    console.log("Signup form submitted:", formData);
    // Handle signup logic here
  };

  if (status === "loading") {
    return (
      <main className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </main>
    );
  }

  if (status === "authenticated") {
    return null;
  }

  return (
    <main className="min-h-screen bg-white">
      <div className="container mx-auto px-4 lg:px-8">
        <div className="flex min-h-screen">
          {/* Left Section - Signup Form */}
          <div className="flex-1 flex items-center justify-center py-12">
            <div className="w-full max-w-md">
              {/* Logo and Header */}
              <div className="mb-8">
                <div className="flex items-center mb-6">
                  <div className="w-8 h-8 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg flex items-center justify-center mr-3">
                    <span className="text-white font-bold text-sm">L</span>
                  </div>
                  <span className="text-xl font-semibold text-gray-900">
                    Luna-VX
                  </span>
                </div>

                <h1 className="text-3xl font-bold text-gray-900 mb-2">
                  Start your
                  <br />
                  intelligent journey.
                </h1>
                <p className="text-gray-600">
                  Join thousands using Luna for smarter web interactions
                </p>
              </div>

              {/* Social Signup */}
              <div className="space-y-3 mb-6">
                <button
                  onClick={() => signIn("google", { callbackUrl: "/chat" })}
                  className="w-full flex items-center justify-center px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <IconBrandGoogle className="w-5 h-5 mr-3" />
                  <span className="font-medium">Continue with Google</span>
                </button>

                <button
                  onClick={() => signIn("github", { callbackUrl: "/chat" })}
                  className="w-full flex items-center justify-center px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <IconBrandGithub className="w-5 h-5 mr-3" />
                  <span className="font-medium">Continue with GitHub</span>
                </button>
              </div>

              {/* Divider */}
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">OR</span>
                </div>
              </div>

              {/* Signup Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label
                      htmlFor="firstName"
                      className="block text-sm font-medium text-gray-700 mb-2"
                    >
                      First name
                    </Label>
                    <Input
                      id="firstName"
                      name="firstName"
                      type="text"
                      placeholder="Tyler"
                      value={formData.firstName}
                      onChange={handleInputChange}
                      className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <Label
                      htmlFor="lastName"
                      className="block text-sm font-medium text-gray-700 mb-2"
                    >
                      Last name
                    </Label>
                    <Input
                      id="lastName"
                      name="lastName"
                      type="text"
                      placeholder="Durden"
                      value={formData.lastName}
                      onChange={handleInputChange}
                      className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                      required
                    />
                  </div>
                </div>

                <div>
                  <Label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Work email
                  </Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="tyler@company.com"
                    value={formData.email}
                    onChange={handleInputChange}
                    className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                    required
                  />
                </div>

                <div>
                  <Label
                    htmlFor="company"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Company <span className="text-gray-400">(optional)</span>
                  </Label>
                  <Input
                    id="company"
                    name="company"
                    type="text"
                    placeholder="Your company"
                    value={formData.company}
                    onChange={handleInputChange}
                    className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                  />
                </div>

                <div>
                  <Label
                    htmlFor="password"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Password
                  </Label>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    placeholder="Create a strong password"
                    value={formData.password}
                    onChange={handleInputChange}
                    className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                    required
                    minLength={8}
                  />
                </div>

                <button
                  type="submit"
                  className="w-full bg-black text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-800 transition-colors flex items-center justify-center"
                >
                  Create account
                  <IconArrowRight className="w-4 h-4 ml-2" />
                </button>
              </form>

              {/* Terms */}
              <p className="mt-4 text-xs text-gray-500 text-center">
                By creating an account, you agree to our{" "}
                <Link href="/terms" className="text-purple-600 hover:underline">
                  Terms of Service
                </Link>{" "}
                and{" "}
                <Link
                  href="/privacy"
                  className="text-purple-600 hover:underline"
                >
                  Privacy Policy
                </Link>
              </p>

              {/* Login Link */}
              <div className="mt-6 text-center">
                <span className="text-sm text-gray-600">
                  Already have an account?{" "}
                  <Link
                    href="/login"
                    className="text-purple-600 hover:underline font-medium"
                  >
                    Sign in
                  </Link>
                </span>
              </div>
            </div>
          </div>

          {/* Right Section - Capabilities & Pricing */}
          <div className="hidden lg:flex flex-1 items-center justify-center p-12 bg-gray-50">
            <div className="max-w-lg">
              {/* Animated Capability Card */}
              <div className="bg-white rounded-2xl shadow-lg p-8 mb-8 transform transition-all duration-500">
                <div className="text-4xl mb-4">
                  {lunaCapabilities[currentCapability].icon}
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">
                  {lunaCapabilities[currentCapability].title}
                </h3>
                <p className="text-gray-600 mb-4">
                  {lunaCapabilities[currentCapability].description}
                </p>
                <ul className="space-y-2">
                  {lunaCapabilities[currentCapability].features.map(
                    (feature, index) => (
                      <li
                        key={index}
                        className="flex items-center text-sm text-gray-700"
                      >
                        <IconCheck className="w-4 h-4 text-green-600 mr-2 flex-shrink-0" />
                        {feature}
                      </li>
                    ),
                  )}
                </ul>
              </div>

              {/* Quick Pricing Preview */}
              <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl p-6 text-white">
                <h4 className="font-bold text-lg mb-2">Start Free Today</h4>
                <p className="text-purple-100 mb-4 text-sm">
                  Begin with our free tier and upgrade as you grow
                </p>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold">100</div>
                    <div className="text-xs text-purple-200">
                      requests/month
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold">$0</div>
                    <div className="text-xs text-purple-200">forever</div>
                  </div>
                </div>
              </div>

              {/* Capability Navigation Dots */}
              <div className="flex justify-center space-x-2 mt-8">
                {lunaCapabilities.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentCapability(index)}
                    className={cn(
                      "w-2 h-2 rounded-full transition-colors",
                      index === currentCapability
                        ? "bg-purple-600"
                        : "bg-gray-300",
                    )}
                  />
                ))}
              </div>

              {/* Trust Indicators */}
              <div className="mt-8 space-y-3">
                <div className="flex items-center space-x-3 text-sm text-gray-600">
                  <IconCheck className="w-4 h-4 text-green-600" />
                  <span>SOC 2 Type II Certified</span>
                </div>
                <div className="flex items-center space-x-3 text-sm text-gray-600">
                  <IconCheck className="w-4 h-4 text-green-600" />
                  <span>GDPR Compliant</span>
                </div>
                <div className="flex items-center space-x-3 text-sm text-gray-600">
                  <IconCheck className="w-4 h-4 text-green-600" />
                  <span>99.9% Uptime SLA</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
