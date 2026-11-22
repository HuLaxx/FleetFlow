import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required by the frontend Dockerfile's standalone Node server.
  output: "standalone",
};

export default nextConfig;
