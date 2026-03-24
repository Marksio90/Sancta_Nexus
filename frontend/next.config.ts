import type { NextConfig } from "next";

// BUILD_TARGET=mobile → static export for Capacitor (iOS/Android)
// BUILD_TARGET unset   → standalone Docker image
const isMobileBuild = process.env.BUILD_TARGET === "mobile";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: isMobileBuild ? "export" : "standalone",

  // Required for static export (Capacitor)
  ...(isMobileBuild && {
    images: { unoptimized: true },
    trailingSlash: true,
  }),
};

export default nextConfig;
