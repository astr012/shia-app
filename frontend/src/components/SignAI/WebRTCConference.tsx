'use client';

import { useRef, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Video, PhoneOff } from 'lucide-react';

interface WebRTCConferenceProps {
  remoteStream: MediaStream | null;
  remoteSubtitle: string | null;
  onEndCall: () => void;
}

export default function WebRTCConference({ remoteStream, remoteSubtitle, onEndCall }: WebRTCConferenceProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current && remoteStream) {
      videoRef.current.srcObject = remoteStream;
    }
  }, [remoteStream]);

  if (!remoteStream) {
    return null; /* Hide if not active */
  }

  return (
    <div className="relative w-full aspect-video border-4 border-matrix/50 scanlines bg-deep-black overflow-hidden flex items-center justify-center mt-6">
      {/* Remote Video Stream */}
      <video
        ref={videoRef}
        className="absolute inset-0 w-full h-full object-cover"
        autoPlay
        playsInline
      />

      {/* Connection Indicator */}
      <motion.div
        className="absolute top-4 left-4 text-[10px] text-green-400 font-mono bg-black/60 px-2 py-1 border border-green-400 z-20 flex items-center gap-1"
        animate={{ opacity: [0.4, 0.8, 0.4] }}
        transition={{ duration: 3, repeat: Infinity }}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
        SECURE P2P LINK ACTIVE
      </motion.div>

      {/* End Call Button */}
      <button 
        onClick={onEndCall}
        className="absolute top-4 right-4 bg-red-600/80 text-white p-2 border border-red-500 hover:bg-red-500 transition-colors z-20"
      >
        <PhoneOff size={16} />
      </button>

      {/* P2P Translated Subtitle Overlay */}
      {remoteSubtitle && (
        <motion.div 
          className="absolute bottom-10 left-0 w-full flex justify-center z-20"
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          key={remoteSubtitle}
        >
          <div className="bg-black/80 text-yellow-300 font-pixel text-xl px-6 py-3 border border-yellow-500/50 max-w-[80%] text-center leading-relaxed">
            "{remoteSubtitle}"
          </div>
        </motion.div>
      )}
    </div>
  );
}
