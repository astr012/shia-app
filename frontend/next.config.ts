import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  images: {
    unoptimized: true,
  },
  serverExternalPackages: [
    "@mediapipe/hands",
    "@mediapipe/camera_utils",
    "@mediapipe/pose",
    "@mediapipe/face_mesh",
  ],
};

export default nextConfig;
