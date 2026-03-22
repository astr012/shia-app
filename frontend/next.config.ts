import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  images: {
    unoptimized: true,
  },
  serverExternalPackages: ["@mediapipe/hands", "@mediapipe/camera_utils"],
};

export default nextConfig;
