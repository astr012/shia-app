'use client';

// ============================================================
// SHIA — Main Application Page
// Wires the pipeline orchestrator + server health into the UI
// ============================================================

import { usePipeline } from '@/hooks/usePipeline';
import { useServerHealth } from '@/hooks/useServerHealth';
import Header from '@/components/SignAI/Header';
import VisionMatrix from '@/components/SignAI/VisionMatrix';
import QuickActions from '@/components/SignAI/QuickActions';
import TranscriptLog from '@/components/SignAI/TranscriptLog';
import SignPlayer from '@/components/SignAI/SignPlayer';
import Footer from '@/components/SignAI/Footer';
import WebRTCConference from '@/components/SignAI/WebRTCConference';
import { useDatabaseFailover } from '@/hooks/useDatabaseFailover';
import { useWebRTC } from '@/hooks/useWebRTC';
import { useEffect, useState } from 'react';

export default function Home() {
  const {
    // Pipeline state
    isActive,
    mode,
    logs,
    wsStatus,
    signSequence,
    signSourceText,
    signProcessingTime,

    // Pipeline actions
    startPipeline,
    stopPipeline,
    toggleMode,
    sendManualInput,
    processGestureResult,
    ws,
    lastMessage,
    sessionId,
  } = usePipeline();

  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [remoteSubtitle, setRemoteSubtitle] = useState<string | null>(null);
  const [targetSessionInput, setTargetSessionInput] = useState('');

  const {
    remoteStream,
    initiateCall,
    handleIncomingOffer,
    handleIncomingAnswer,
    handleIncomingICE,
    sendSubtitle,
    endCall
  } = useWebRTC({
    ws,
    localStream,
    onSubtitleReceived: setRemoteSubtitle
  });

  // Handle incoming WebRTC signaling messages
  useEffect(() => {
    if (!lastMessage) return;

    const { type, payload } = lastMessage;
    const { from_session, data } = (payload as any) || {};

    if (type === 'webrtc_offer' && data) {
      handleIncomingOffer(from_session, data);
    } else if (type === 'webrtc_answer' && data) {
      handleIncomingAnswer(data);
    } else if (type === 'webrtc_ice' && data) {
      handleIncomingICE(data);
    } else if (type === 'webrtc_fallback_subtitle' && data) {
      setRemoteSubtitle(data);
    }
  }, [lastMessage, handleIncomingOffer, handleIncomingAnswer, handleIncomingICE]);

  // Route local speech/gestures to remote peer
  useEffect(() => {
    if (remoteStream && logs.length > 0) {
      const latestLog = logs[logs.length - 1];
      if (latestLog.text.startsWith('[TRANSLATED]:')) {
        const text = latestLog.text.match(/"([^"]+)"/)?.[1];
        if (text) {
          sendSubtitle(text); 
        }
      }
    }
  }, [logs, remoteStream, sendSubtitle]);

  // Server health polling (always on for status tiles)
  const {
    health,
    isReachable,
    latencyMs,
  } = useServerHealth({ enabled: true });

  const { attemptResync } = useDatabaseFailover();

  // Edge State Resilience: Automatically flush offline IndexedDB queue when backend becomes reachable
  useEffect(() => {
    if (isReachable) {
      attemptResync();
    }
  }, [isReachable, attemptResync]);

  const handleToggleSystem = () => {
    if (isActive) {
      stopPipeline();
    } else {
      startPipeline();
    }
  };

  return (
    <div className="bg-pixel-grid min-h-screen p-4 md:p-8 font-mono">
      {/* Header — System Controls */}
      <Header
        isSystemActive={isActive}
        mode={mode}
        onToggleMode={toggleMode}
        onToggleSystem={handleToggleSystem}
      />

      {/* Main Terminal UI */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-7xl mx-auto">
        {/* Left Column: Vision + Sign Player + Quick Actions */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <VisionMatrix
            isActive={isActive}
            onGestureResult={processGestureResult}
            onStreamAvailable={setLocalStream}
          />

          {/* P2P WebRTC Video Call */}
          <WebRTCConference
            remoteStream={remoteStream}
            remoteSubtitle={remoteSubtitle}
            onEndCall={endCall}
          />

          {/* WebRTC Controls */}
          {isActive && (
            <div className="bg-deep-black border border-matrix/30 p-4 font-mono text-sm">
              <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                <div className="text-matrix">
                  <span className="text-gray-500">YOUR SESSION ID: </span>
                  <span className="font-bold">{sessionId || 'AWAITING CONNECTION...'}</span>
                </div>
                
                {!remoteStream && (
                  <div className="flex gap-2 w-full md:w-auto">
                    <input 
                      type="text" 
                      placeholder="TARGET SESSION ID" 
                      className="bg-black border border-matrix/50 text-white px-3 py-1 outline-none focus:border-matrix w-full md:w-64"
                      value={targetSessionInput}
                      onChange={(e) => setTargetSessionInput(e.target.value)}
                    />
                    <button 
                      onClick={() => initiateCall(targetSessionInput)}
                      disabled={!targetSessionInput || !sessionId}
                      className="bg-matrix text-black px-4 py-1 hover:bg-matrix/80 disabled:opacity-50 transition-colors font-bold whitespace-nowrap"
                    >
                      CONNECT P2P
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Sign Language Visualization Player */}
          <SignPlayer
            signSequence={signSequence}
            sourceText={signSourceText}
            processingTimeMs={signProcessingTime}
            isVisible={isActive && signSequence.length > 0}
          />

          <QuickActions
            isActive={isActive}
            wsStatus={wsStatus}
            latencyMs={latencyMs}
            isServerReachable={isReachable}
            grammarEngine={health?.services.grammar_engine || 'unknown'}
            translationEngine={health?.services.translation_engine || 'unknown'}
            activeConnections={health?.services.active_connections || 0}
            serverUptime={health?.uptime || '—'}
          />
        </div>

        {/* Right Column: Transcript Log */}
        <div className="lg:col-span-5">
          <TranscriptLog
            logs={logs}
            isActive={isActive}
            onManualInput={sendManualInput}
          />
        </div>
      </main>

      {/* Footer */}
      <Footer
        serverVersion={health?.version}
        isServerReachable={isReachable}
      />
    </div>
  );
}

