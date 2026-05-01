'use client';

// ============================================================
// Shia — Vision Matrix Component (Camera / Tracking View)
// NOW with REAL camera feed + MediaPipe hand tracking overlay
// ============================================================

import { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, Camera, AlertTriangle } from 'lucide-react';
import { useMediaPipe, HandTrackingResult } from '@/hooks/useMediaPipe';

interface VisionMatrixProps {
  isActive: boolean;
  onGestureResult?: (result: HandTrackingResult) => void;
}

export default function VisionMatrix({ isActive, onGestureResult }: VisionMatrixProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cameraPermission, setCameraPermission] = useState<'prompt' | 'granted' | 'denied'>('prompt');

  const {
    isLoading,
    isTracking,
    error,
    fps,
    lastResult,
    deviceTier,
    isShedding,
  } = useMediaPipe({
    videoRef,
    canvasRef,
    enabled: isActive,
    maxHands: 2,
    onResult: (result) => {
      onGestureResult?.(result);
    },
    onError: (err) => {
      console.error('[VisionMatrix] Error:', err);
      if (err.includes('denied') || err.includes('NotAllowed')) {
        setCameraPermission('denied');
      }
    },
  });

  // Derive camera permission from tracking state
  const derivedPermission = isTracking ? 'granted' : cameraPermission;

  return (
    <div className="flex flex-col gap-4">
      {/* Section Title */}
      <div className="flex justify-between items-end">
        <h2 className="font-pixel text-2xl text-matrix">{'/// VISUAL_INPUT_MATRIX'}</h2>
        <div className="flex items-center gap-3">
          {isActive && (
            <motion.span
              className="text-xs text-matrix font-mono"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {isTracking ? '● LIVE' : isLoading ? '○ LOADING...' : '○ STANDBY'}
            </motion.span>
          )}
          <motion.span
            className="text-xs text-gray-500 bg-black border border-gray-800 px-2 py-1 font-mono"
            animate={isActive ? { opacity: [1, 0.5, 1] } : {}}
            transition={{ duration: 2, repeat: Infinity }}
          >
            FPS: {isActive ? (fps > 0 ? fps.toFixed(1) : '30.0') : '0.0'}
            {isShedding && <span className="text-red-500 ml-2 animate-pulse">[MODELS SHED]</span>}
          </motion.span>
        </div>
      </div>

      {/* Camera Feed Area */}
      <div
        className={`relative w-full aspect-video border-4 border-white scanlines bg-deep-black overflow-hidden flex items-center justify-center transition-all ${
          isActive ? 'pixel-shadow-white' : ''
        }`}
      >
        {/* Corner Brackets */}
        {['top-0 left-0 border-t-4 border-l-4', 'top-0 right-0 border-t-4 border-r-4', 'bottom-0 left-0 border-b-4 border-l-4', 'bottom-0 right-0 border-b-4 border-r-4'].map(
          (pos, i) => (
            <motion.div
              key={i}
              className={`absolute w-8 h-8 border-matrix m-4 z-20 ${pos}`}
              animate={isActive ? { opacity: [0.5, 1, 0.5] } : { opacity: 0.2 }}
              transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
            />
          )
        )}

        {/* Hidden Video Element (camera feed source) */}
        <video
          ref={videoRef}
          className={`absolute inset-0 w-full h-full object-cover ${isActive && isTracking ? 'opacity-70' : 'opacity-0'}`}
          autoPlay
          playsInline
          muted
          style={{ transform: 'scaleX(-1)' }}  /* Mirror for selfie view */
        />

        {/* Canvas Overlay (MediaPipe landmark drawings) — adaptive resolution */}
        <canvas
          ref={canvasRef}
          className={`absolute inset-0 w-full h-full z-10 ${isActive && isTracking ? '' : 'hidden'}`}
          width={deviceTier === 'low' ? 320 : 640}
          height={deviceTier === 'low' ? 240 : 480}
          style={{ transform: 'scaleX(-1)' }}  /* Mirror to match video */
        />

        <AnimatePresence mode="wait">
          {!isActive ? (
            /* ── OFFLINE STATE ── */
            <motion.div
              key="offline"
              className="text-center z-20"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
            >
              <Eye size={48} className="mx-auto mb-4 text-gray-700" />
              <p className="font-pixel text-xl text-gray-600 tracking-widest">CAMERA OFFLINE</p>
              <p className="font-mono text-xs text-gray-700 mt-2">PRESS INITIALIZE TO BEGIN</p>
            </motion.div>
          ) : error || derivedPermission === 'denied' ? (
            /* ── ERROR / PERMISSION DENIED STATE ── */
            <motion.div
              key="error"
              className="text-center z-20 px-8"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <AlertTriangle size={48} className="mx-auto mb-4 text-yellow-500" />
              <p className="font-pixel text-lg text-yellow-500 tracking-widest mb-2">CAMERA ACCESS DENIED</p>
              <p className="font-mono text-xs text-gray-400 max-w-md">
                {error || 'Please allow camera access in your browser settings and reload the page.'}
              </p>
              <p className="font-mono text-xs text-gray-600 mt-4">
                RUNNING IN SIMULATION MODE...
              </p>
            </motion.div>
          ) : isLoading ? (
            /* ── LOADING STATE ── */
            <motion.div
              key="loading"
              className="text-center z-20"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Camera size={48} className="mx-auto mb-4 text-matrix animate-pulse" />
              <p className="font-pixel text-xl text-matrix tracking-widest">INITIALIZING CAMERA...</p>
              <p className="font-mono text-xs text-gray-500 mt-2">REQUESTING PERMISSIONS</p>
            </motion.div>
          ) : isTracking ? (
            /* ── ACTIVE TRACKING OVERLAYS ── */
            <motion.div
              key="tracking-overlay"
              className="absolute inset-0 z-10 pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Detected gesture label */}
              {lastResult?.gesture && (
                <motion.div
                  className="absolute top-4 left-4 bg-matrix text-black text-sm font-bold px-2 py-1 font-mono z-20"
                  initial={{ x: -20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  key={lastResult.gesture}
                >
                  GESTURE: {lastResult.gesture} [{(lastResult.confidence * 100).toFixed(1)}%]
                </motion.div>
              )}

              {/* Live Readout Overlay */}
              <motion.div
                className="absolute bottom-4 left-4 flex flex-col gap-1 text-xs text-matrix bg-black/80 px-3 py-2 border border-matrix/30 font-mono z-20"
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                {lastResult?.landmarks?.[0] ? (
                  <>
                    <span>X: {(lastResult.landmarks[0][0]?.x * 640).toFixed(2)} | Y: {(lastResult.landmarks[0][0]?.y * 480).toFixed(2)}</span>
                    <span>Z_DEPTH: {lastResult.landmarks[0][0]?.z?.toFixed(3) || '0.000'}</span>
                    <span>HANDS: {lastResult.landmarks.length} | JOINTS: {lastResult.landmarks[0]?.length || 0}</span>
                  </>
                ) : (
                  <>
                    <motion.span animate={{ opacity: [0.6, 1, 0.6] }} transition={{ duration: 2, repeat: Infinity }}>
                      SCANNING FOR HANDS...
                    </motion.span>
                    <span>POSTURE_CONF: WAITING</span>
                  </>
                )}
              </motion.div>

              {/* Top-right REC indicator */}
              <motion.div
                className="absolute top-4 right-4 text-[10px] text-matrix/80 font-mono bg-black/60 px-2 py-1 border border-matrix/20 z-20 flex items-center gap-1"
                animate={{ opacity: [0.4, 0.8, 0.4] }}
                transition={{ duration: 3, repeat: Infinity }}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                REC | {deviceTier.toUpperCase()}
              </motion.div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}
