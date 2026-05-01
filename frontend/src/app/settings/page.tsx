'use client';

// ============================================================
// SignAI_OS — Settings Page
//
// Configurable options: TTS voice, backend URL, theme,
// and system information display.
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import {
  ArrowLeft,
  Volume2,
  Wifi,
  Monitor,
  Info,
  Save,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────

interface SettingsState {
  apiUrl: string;
  ttsRate: number;
  ttsPitch: number;
  ttsVoice: string;
  autoReconnect: boolean;
  showFps: boolean;
  gestureConfidenceThreshold: number;
}

const DEFAULT_SETTINGS: SettingsState = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || '',
  ttsRate: 1.0,
  ttsPitch: 1.0,
  ttsVoice: '',
  autoReconnect: true,
  showFps: false,
  gestureConfidenceThreshold: 0.7,
};

// ── Helpers ──────────────────────────────────────────────────

function loadSettings(): SettingsState {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;
  try {
    const stored = localStorage.getItem('shia_settings');
    if (stored) return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
  } catch { /* ignore */ }
  return DEFAULT_SETTINGS;
}

function saveSettings(settings: SettingsState) {
  localStorage.setItem('shia_settings', JSON.stringify(settings));
}

// ── Sub-components ───────────────────────────────────────────

function SectionHeader({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <div className="flex items-center gap-3 mb-4 mt-8 first:mt-0">
      <Icon size={18} className="text-matrix" />
      <h2 className="font-pixel text-xl text-white tracking-wider uppercase">{title}</h2>
      <div className="flex-1 h-px bg-white/10" />
    </div>
  );
}

function SettingRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-3 border-b border-white/5">
      <div>
        <p className="text-sm font-mono text-white">{label}</p>
        {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
      </div>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-12 h-6 border-2 transition-colors cursor-pointer ${
        checked ? 'border-matrix bg-matrix/20' : 'border-gray-600 bg-black'
      }`}
    >
      <motion.div
        className={`absolute top-0.5 w-4 h-4 ${checked ? 'bg-matrix' : 'bg-gray-500'}`}
        animate={{ left: checked ? '24px' : '2px' }}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      />
    </button>
  );
}

function Slider({
  value,
  onChange,
  min = 0,
  max = 2,
  step = 0.1,
  label,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-32 accent-[#00FF41] cursor-pointer"
      />
      <span className="font-mono text-xs text-matrix w-10 text-right">{label}</span>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsState>(() => loadSettings());
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [saved, setSaved] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [backendVersion, setBackendVersion] = useState<string | null>(null);

  // Load available TTS voices
  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const loadVoices = () => {
      const v = window.speechSynthesis.getVoices();
      setVoices(v);
      // Set default voice if none selected
      if (!settings.ttsVoice && v.length > 0) {
        const defaultVoice = v.find(voice => voice.default) || v[0];
        setSettings(prev => ({ ...prev, ttsVoice: defaultVoice.name }));
      }
    };

    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
  }, [settings.ttsVoice]);

  // Check backend connectivity
  const checkBackend = useCallback(async () => {
    setBackendStatus('checking');
    try {
      const res = await fetch(`${settings.apiUrl}/health`, {
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const data = await res.json();
        setBackendStatus('online');
        setBackendVersion(data.version);
      } else {
        setBackendStatus('offline');
      }
    } catch {
      setBackendStatus('offline');
      setBackendVersion(null);
    }
  }, [settings.apiUrl]);

  useEffect(() => {
    const timer = setTimeout(checkBackend, 0);
    return () => clearTimeout(timer);
  }, [checkBackend]);

  // Update a single setting
  const update = <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  // Save to localStorage
  const handleSave = () => {
    saveSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  // Reset to defaults
  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS);
    saveSettings(DEFAULT_SETTINGS);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  // Preview TTS
  const previewVoice = () => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance('Hello! SHIA system is operational.');
    utter.rate = settings.ttsRate;
    utter.pitch = settings.ttsPitch;
    const voice = voices.find(v => v.name === settings.ttsVoice);
    if (voice) utter.voice = voice;
    window.speechSynthesis.speak(utter);
  };

  return (
    <main className="min-h-screen bg-background text-foreground bg-pixel-grid p-6 md:p-10 max-w-3xl mx-auto">
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-8">
        <Link href="/">
          <motion.div
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors cursor-pointer"
            whileHover={{ x: -4 }}
          >
            <ArrowLeft size={18} />
            <span className="font-mono text-sm uppercase">Back</span>
          </motion.div>
        </Link>

        <div className="flex gap-3">
          <motion.button
            onClick={handleReset}
            className="flex items-center gap-2 border border-white/20 text-gray-400 px-4 py-2 text-xs font-mono uppercase hover:border-white/40 hover:text-white transition-colors cursor-pointer"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
          >
            <RotateCcw size={14} />
            Reset
          </motion.button>
          <motion.button
            onClick={handleSave}
            className="flex items-center gap-2 bg-matrix text-black px-4 py-2 text-xs font-bold uppercase pixel-shadow border-2 border-black cursor-pointer"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97, x: 4, y: 4, boxShadow: '2px 2px 0px 0px rgba(0,255,65,0.8)' }}
          >
            <Save size={14} />
            Save
          </motion.button>
        </div>
      </div>

      {/* ── Save confirmation ── */}
      <AnimatePresence>
        {saved && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-center gap-2 bg-matrix/10 border border-matrix/30 px-4 py-2 mb-6"
          >
            <CheckCircle size={16} className="text-matrix" />
            <span className="font-mono text-xs text-matrix">Settings saved successfully</span>
          </motion.div>
        )}
      </AnimatePresence>

      <h1 className="font-pixel text-4xl text-white tracking-widest uppercase mb-2">Settings</h1>
      <p className="font-mono text-xs text-gray-500 mb-8">SYSTEM CONFIGURATION &amp; PREFERENCES</p>

      {/* ═══════ CONNECTION ═══════ */}
      <SectionHeader icon={Wifi} title="Connection" />

      <SettingRow label="Backend API URL" description="WebSocket and REST endpoint">
        <input
          type="text"
          value={settings.apiUrl}
          onChange={(e) => update('apiUrl', e.target.value)}
          className="bg-black border border-white/20 text-white font-mono text-xs px-3 py-1.5 w-64 focus:border-matrix focus:outline-none"
        />
      </SettingRow>

      <SettingRow label="Backend Status">
        <div className="flex items-center gap-2">
          {backendStatus === 'checking' && (
            <span className="text-xs font-mono text-yellow-400">CHECKING...</span>
          )}
          {backendStatus === 'online' && (
            <>
              <div className="w-2 h-2 bg-matrix" />
              <span className="text-xs font-mono text-matrix">ONLINE</span>
              {backendVersion && (
                <span className="text-xs font-mono text-gray-500">v{backendVersion}</span>
              )}
            </>
          )}
          {backendStatus === 'offline' && (
            <>
              <AlertTriangle size={14} className="text-red-400" />
              <span className="text-xs font-mono text-red-400">UNREACHABLE</span>
            </>
          )}
          <motion.button
            onClick={checkBackend}
            className="text-gray-500 hover:text-white ml-2 cursor-pointer"
            whileHover={{ rotate: 180 }}
            transition={{ duration: 0.3 }}
          >
            <RotateCcw size={14} />
          </motion.button>
        </div>
      </SettingRow>

      <SettingRow label="Auto-Reconnect" description="Automatically reconnect WebSocket on disconnect">
        <Toggle checked={settings.autoReconnect} onChange={(v) => update('autoReconnect', v)} />
      </SettingRow>

      {/* ═══════ VOICE ═══════ */}
      <SectionHeader icon={Volume2} title="Text-to-Speech" />

      <SettingRow label="Voice" description="TTS voice for spoken output">
        <select
          value={settings.ttsVoice}
          onChange={(e) => update('ttsVoice', e.target.value)}
          className="bg-black border border-white/20 text-white font-mono text-xs px-3 py-1.5 w-64 focus:border-matrix focus:outline-none cursor-pointer"
        >
          {voices.length === 0 && <option>Loading voices...</option>}
          {voices.map((v) => (
            <option key={v.name} value={v.name}>
              {v.name} ({v.lang})
            </option>
          ))}
        </select>
      </SettingRow>

      <SettingRow label="Speech Rate" description="How fast the voice speaks">
        <Slider value={settings.ttsRate} onChange={(v) => update('ttsRate', v)} min={0.5} max={2} step={0.1} label={`${settings.ttsRate.toFixed(1)}×`} />
      </SettingRow>

      <SettingRow label="Pitch" description="Voice pitch">
        <Slider value={settings.ttsPitch} onChange={(v) => update('ttsPitch', v)} min={0} max={2} step={0.1} label={settings.ttsPitch.toFixed(1)} />
      </SettingRow>

      <SettingRow label="Preview">
        <motion.button
          onClick={previewVoice}
          className="flex items-center gap-2 border border-matrix/50 text-matrix px-4 py-1.5 text-xs font-mono uppercase hover:bg-matrix/10 transition-colors cursor-pointer"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
        >
          <Volume2 size={14} />
          Test Voice
        </motion.button>
      </SettingRow>

      {/* ═══════ DISPLAY ═══════ */}
      <SectionHeader icon={Monitor} title="Display" />

      <SettingRow label="Show FPS Overlay" description="Display frames-per-second on camera view">
        <Toggle checked={settings.showFps} onChange={(v) => update('showFps', v)} />
      </SettingRow>

      <SettingRow label="Gesture Confidence" description="Min confidence to register a gesture (0-1)">
        <Slider
          value={settings.gestureConfidenceThreshold}
          onChange={(v) => update('gestureConfidenceThreshold', v)}
          min={0.3}
          max={1.0}
          step={0.05}
          label={`${(settings.gestureConfidenceThreshold * 100).toFixed(0)}%`}
        />
      </SettingRow>

      {/* ═══════ SYSTEM INFO ═══════ */}
      <SectionHeader icon={Info} title="System Info" />

      <div className="border border-white/10 bg-black/50 p-4 font-mono text-xs text-gray-400 space-y-1">
        <div className="flex justify-between">
          <span>App</span>
          <span className="text-white">SHIA (SignAI_OS)</span>
        </div>
        <div className="flex justify-between">
          <span>Frontend</span>
          <span className="text-white">Next.js + MediaPipe</span>
        </div>
        <div className="flex justify-between">
          <span>Backend</span>
          <span className={backendStatus === 'online' ? 'text-matrix' : 'text-red-400'}>
            {backendStatus === 'online' ? `FastAPI v${backendVersion}` : 'Not connected'}
          </span>
        </div>
        <div className="flex justify-between">
          <span>API URL</span>
          <span className="text-gray-500">{settings.apiUrl}</span>
        </div>
        <div className="flex justify-between">
          <span>Repo</span>
          <a href="https://github.com/astr012/shia-app" target="_blank" rel="noopener noreferrer" className="text-matrix hover:underline">
            github.com/astr012/shia-app
          </a>
        </div>
      </div>

      <div className="h-12" />
    </main>
  );
}
