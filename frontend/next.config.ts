import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,
  images: {
    unoptimized: true,
  },
  serverExternalPackages: ["@mediapipe/hands", "@mediapipe/camera_utils"],
};

export default nextConfig;
