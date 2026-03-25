'use client';

// ============================================================
// PIPELINE LAYER 4: WebRTC Peer-to-Peer Visual Conferencing
//
// Establishes secure P2P video connections and DataChannels.
// Features a "Hole-Punching" state awareness architecture.
// If symmetric NAT routers block direct pathways, it executes
// an automatic fail-over, rerouting data frames transparently 
// over the established secure WebSocket relay.
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';

interface UseWebRTCOptions {
  localVideoRef: React.RefObject<HTMLVideoElement | null>;
  remoteVideoRef: React.RefObject<HTMLVideoElement | null>;
  wsSend: (type: string, payload: any) => void;
  onDataReceived?: (data: any) => void;
}

const ICE_SERVERS = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:global.stun.twilio.com:3478' }
  ]
};

export function useWebRTC({ localVideoRef, remoteVideoRef, wsSend, onDataReceived }: UseWebRTCOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [isFallbackMode, setIsFallbackMode] = useState(false);
  const [remoteId, setRemoteId] = useState<string | null>(null);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const channelRef = useRef<RTCDataChannel | null>(null);

  // ── Connection Boilerplate ──────────────────────────────
  const initPeerConnection = useCallback((targetId: string) => {
    if (pcRef.current) pcRef.current.close();
    
    setRemoteId(targetId);
    setIsFallbackMode(false);

    const pc = new RTCPeerConnection(ICE_SERVERS);
    pcRef.current = pc;

    // Stream Local Video
    if (localVideoRef.current && localVideoRef.current.srcObject) {
      const stream = localVideoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => pc.addTrack(track, stream));
    }

    // Capture Remote Video
    pc.ontrack = (event) => {
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = event.streams[0];
      }
    };

    // ICE Candidate Exchange
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        wsSend('webrtc_signal', {
          target_id: targetId,
          signal_data: { type: 'ice-candidate', candidate: event.candidate }
        });
      }
    };

    // ── Self-Healing Fail-Safe (NAT Block Detection) ──
    pc.oniceconnectionstatechange = () => {
      console.log(`[WebRTC] ICE State: ${pc.iceConnectionState}`);
      if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected') {
         console.warn('[Self-Healing] Symmetric NAT or firewall block detected. WebRTC Hole-Punching failed.');
         console.warn('[Self-Healing] Falling back to secure WebSocket data relay bypassing P2P tunnel.');
         setIsFallbackMode(true);
         setIsConnected(false);
      } else if (pc.iceConnectionState === 'connected') {
         setIsConnected(true);
         setIsFallbackMode(false);
      }
    };

    return pc;
  }, [localVideoRef, remoteVideoRef, wsSend]);

  const initDataChannel = useCallback((pc: RTCPeerConnection) => {
    const channel = pc.createDataChannel('signai_data');
    channelRef.current = channel;

    channel.onopen = () => console.log('[WebRTC] DataChannel Open');
    channel.onmessage = (event) => {
      onDataReceived?.(JSON.parse(event.data));
    };

    pc.ondatachannel = (event) => {
      const receiveChannel = event.channel;
      receiveChannel.onmessage = (e) => onDataReceived?.(JSON.parse(e.data));
      channelRef.current = receiveChannel;
    };
  }, [onDataReceived]);

  // ── Call Operations ──────────────────────────────────────
  const callPeer = async (targetId: string) => {
    const pc = initPeerConnection(targetId);
    initDataChannel(pc);

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    wsSend('webrtc_signal', {
      target_id: targetId,
      signal_data: { type: 'offer', offer }
    });
  };

  const handleIncomingSignal = async (sourceId: string, signal: any) => {
    let pc = pcRef.current;
    
    if (signal.type === 'offer') {
      pc = initPeerConnection(sourceId);
      initDataChannel(pc);
      await pc.setRemoteDescription(new RTCSessionDescription(signal.offer));
      
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      
      wsSend('webrtc_signal', {
        target_id: sourceId,
        signal_data: { type: 'answer', answer }
      });
    } else if (signal.type === 'answer' && pc) {
      await pc.setRemoteDescription(new RTCSessionDescription(signal.answer));
    } else if (signal.type === 'ice-candidate' && pc) {
      await pc.addIceCandidate(new RTCIceCandidate(signal.candidate));
    }
  };

  // ── Data Transmission (Self-Healing Router) ─────────────
  const sendData = useCallback((data: any) => {
    const payload = JSON.stringify(data);
    
    // Normal WebRTC P2P
    if (channelRef.current && channelRef.current.readyState === 'open' && !isFallbackMode) {
      channelRef.current.send(payload);
    } 
    // Fail-over to WebSocket Relay Turn-Server alternative
    else if (isFallbackMode && remoteId) {
      wsSend('webrtc_relay', {
        target_id: remoteId,
        relay_data: data
      });
    } else {
      console.warn('[Self-Healing] Dropping transmission: Neither P2P nor Relay is available.');
    }
  }, [isFallbackMode, remoteId, wsSend]);

  const endCall = useCallback(() => {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    setRemoteId(null);
    setIsConnected(false);
    setIsFallbackMode(false);
  }, []);

  return {
    callPeer,
    endCall,
    handleIncomingSignal,
    sendData,
    isConnected,
    isFallbackMode,
    activePeerId: remoteId
  };
}
