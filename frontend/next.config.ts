import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable ESLint during builds to avoid build failures
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Disable TypeScript errors during builds (if needed)
  typescript: {
    ignoreBuildErrors: true,
  },
  // Enable standalone output for Docker deployments
  output: "standalone",

  /* your other config options here */
};

export default nextConfig;
