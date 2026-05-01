'use client';

import { useState, useCallback } from 'react';

interface UseWebRTCOptions {
  ws: WebSocket | null;
  localStream: MediaStream | null;
  onSubtitleReceived?: (subtitle: string) => void;
}

export function useWebRTC({ ws, localStream, onSubtitleReceived }: UseWebRTCOptions) {
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [peerConnection, setPeerConnection] = useState<RTCPeerConnection | null>(null);
  const [dataChannel, setDataChannel] = useState<RTCDataChannel | null>(null);
  const [isUsingFallbackRelay, setIsUsingFallbackRelay] = useState<boolean>(false);
  
  // Create a new Peer Connection
  const initializePeerConnection = useCallback((targetSessionId: string) => {
    // 1. Setup PC with STUN + TURN structures for NAT Hole Punching and Relay Fallback
    const pc = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        // Phase 5 Structural Scaffolding: In production, configure TURN credentials 
        // to relay streaming constraints when symmetric NAT layers block P2P DataChannels.
        {
          urls: process.env.NEXT_PUBLIC_TURN_URL || 'turn:turn.signai.os:3478',
          username: process.env.NEXT_PUBLIC_TURN_USERNAME || 'fallback_relay_user',
          credential: process.env.NEXT_PUBLIC_TURN_PASSWORD || 'fallback_relay_pass'
        }
      ]
    });

    // 2. Add local stream tracks to PC
    if (localStream) {
      localStream.getTracks().forEach((track) => pc.addTrack(track, localStream));
    }

    // 3. Setup Remote stream reception
    pc.ontrack = (event) => {
      if (event.streams && event.streams[0]) {
        setRemoteStream(event.streams[0]);
      }
    };

    // 4. Setup ICE Candidate routing over signaling WS
    pc.onicecandidate = (event) => {
      if (event.candidate && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'webrtc_ice',
          payload: {
            target_session_id: targetSessionId,
            data: event.candidate
          }
        }));
      }
    };

    // 5. Create Data Channel for P2P gesture subtitles
    const dc = pc.createDataChannel('subtitles');
    dc.onmessage = (event) => {
      onSubtitleReceived?.(event.data);
    };
    setDataChannel(dc);

    // 5b. Self-Healing Fail-Safe (Hole-Punching State Awareness)
    pc.oniceconnectionstatechange = () => {
      if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected') {
        console.warn("[WebRTC] Symmetric NAT block detected. Failing over to WebSocket relay.");
        setIsUsingFallbackRelay(true);
      }
    };

    // 6. Handle receiving Data Channel
    pc.ondatachannel = (event) => {
      const receiveChannel = event.channel;
      receiveChannel.onmessage = (e) => {
        onSubtitleReceived?.(e.data);
      };
      setDataChannel(receiveChannel);
    };

    setPeerConnection(pc);
    return pc;
  }, [localStream, ws, onSubtitleReceived]);

  const initiateCall = useCallback(async (targetSessionId: string) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    
    const pc = initializePeerConnection(targetSessionId);
    
    // Create Offer
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    
    // Send Offer via WebSocket Signaling
    ws.send(JSON.stringify({
      type: 'webrtc_offer',
      payload: {
        target_session_id: targetSessionId,
        data: offer
      }
    }));
  }, [initializePeerConnection, ws]);

  const handleIncomingOffer = useCallback(async (fromSessionId: string, offer: RTCSessionDescriptionInit) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    
    const pc = initializePeerConnection(fromSessionId);
    await pc.setRemoteDescription(new RTCSessionDescription(offer));
    
    // Create Answer
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    
    // Send Answer via WebSocket Signaling
    ws.send(JSON.stringify({
      type: 'webrtc_answer',
      payload: {
        target_session_id: fromSessionId,
        data: answer
      }
    }));
  }, [initializePeerConnection, ws]);

  const handleIncomingAnswer = useCallback(async (answer: RTCSessionDescriptionInit) => {
    if (peerConnection) {
      await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
    }
  }, [peerConnection]);

  const handleIncomingICE = useCallback(async (candidate: RTCIceCandidateInit) => {
    if (peerConnection) {
      await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
    }
  }, [peerConnection]);

  const sendSubtitle = useCallback((text: string, remoteSessionId?: string) => {
    // 1. Primary Route: P2P DataChannel
    if (!isUsingFallbackRelay && dataChannel && dataChannel.readyState === 'open') {
      dataChannel.send(text);
      return;
    }
    
    // 2. Self-Healing Fallback: WebSocket Global Relay
    if (isUsingFallbackRelay && ws && ws.readyState === WebSocket.OPEN && remoteSessionId) {
      ws.send(JSON.stringify({
        type: 'webrtc_fallback_subtitle',
        payload: {
          target_session_id: remoteSessionId,
          data: text
        }
      }));
    }
  }, [dataChannel, isUsingFallbackRelay, ws]);

  const endCall = useCallback(() => {
    if (peerConnection) {
      peerConnection.close();
      setPeerConnection(null);
      setRemoteStream(null);
      setDataChannel(null);
    }
  }, [peerConnection]);

  return {
    remoteStream,
    initiateCall,
    handleIncomingOffer,
    handleIncomingAnswer,
    handleIncomingICE,
    sendSubtitle,
    endCall
  };
}
