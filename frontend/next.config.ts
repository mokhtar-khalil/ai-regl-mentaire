import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker deployment (Railway): emits .next/standalone with only the
  // files actually needed to run `node server.js`, no node_modules copy.
  output: "standalone",
};

export default nextConfig;
