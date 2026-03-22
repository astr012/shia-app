// ============================================================
// Shia — Core Type Definitions
// ============================================================

export type TranslationMode = 'SIGN_TO_SPEECH' | 'SPEECH_TO_SIGN';

export type LogSource = 'USER' | 'SYSTEM' | 'AI';

export interface LogEntry {
  id: string;
  source: LogSource;
  text: string;
  timestamp: string;
  confidence?: number;
}

export interface HandLandmark {
  x: number;
  y: number;
  z: number;
  visibility?: number;
}

export interface GestureResult {
  gesture: string;
  confidence: number;
  landmarks: HandLandmark[];
}

export interface SystemStatus {
  isOnline: boolean;
  fps: number;
  latency: number;
  computeMode: 'EDGE_WASM' | 'CLOUD_GPU' | 'HYBRID';
  micActive: boolean;
  cameraActive: boolean;
}

export interface TrackingData {
  objectLabel: string;
  confidence: number;
  x: number;
  y: number;
  zDepth: number;
  postureConfidence: 'HIGH' | 'MEDIUM' | 'LOW';
}
