'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BookOpen, Save, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';
import { useDatabaseFailover } from '@/hooks/useDatabaseFailover';

export default function CustomDialectManager() {
  const { saveOfflineAction, attemptResync, getDialectProfileOffline, saveDialectProfileOffline } = useDatabaseFailover();
  const [gesture, setGesture] = useState('');
  const [meaning, setMeaning] = useState('');
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved_offline' | 'saved_online' | 'error'>('idle');
  const [savedDialects, setSavedDialects] = useState<Array<{ gesture_sequence: string; meaning: string }>>([]);

  const API = process.env.NEXT_PUBLIC_API_URL || '';

  // Attempt to sync offline queue on mount
  useEffect(() => {
    attemptResync();
    
    // Load local cache immediately
    getDialectProfileOffline('local_user').then((profile) => {
      if (profile && Array.isArray((profile as any).entries)) {
        setSavedDialects((profile as any).entries);
      }
    });
  }, [attemptResync, getDialectProfileOffline]);

  const handleSave = async () => {
    if (!gesture || !meaning) return;
    setStatus('saving');

    const payload = { gesture_sequence: gesture, meaning };
    
    // Optimistic UI update
    const newDialects = [...savedDialects, payload];
    setSavedDialects(newDialects);
    saveDialectProfileOffline('local_user', { entries: newDialects });

    try {
      const res = await fetch(`${API}/api/users/custom-words`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Note: In a fully authenticated system, pass the JWT here
          // 'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setStatus('saved_online');
      } else {
        throw new Error('API Error or Unauthorized');
      }
    } catch (e) {
      console.warn('[DialectManager] Network or API error, failing over to IndexedDB.', e);
      // Failover to offline queue
      if (saveOfflineAction) {
        await saveOfflineAction(`${API}/api/users/custom-words`, payload);
        setStatus('saved_offline');
      } else {
        setStatus('error');
      }
    }

    // Reset input
    setTimeout(() => {
      setGesture('');
      setMeaning('');
      setStatus('idle');
    }, 2000);
  };

  const handleManualResync = () => {
    setStatus('saving');
    attemptResync().then(() => {
      setStatus('idle');
    });
  };

  return (
    <div className="border border-white/10 bg-black/40 p-5 font-mono">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <BookOpen size={18} className="text-matrix" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">Custom Dialect Manager</h2>
        </div>
        <button 
          onClick={handleManualResync}
          className="flex items-center gap-2 text-[10px] text-gray-400 hover:text-matrix transition-colors cursor-pointer"
        >
          <RefreshCw size={12} />
          SYNC OFFLINE QUEUE
        </button>
      </div>

      <p className="text-xs text-gray-500 mb-4">
        Map custom gesture sequences to specific meanings. Actions are automatically preserved at the edge via IndexedDB and synchronized when connection is restored.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4">
        <div className="md:col-span-2">
          <input
            type="text"
            placeholder="Gesture (e.g. THUMB_UP)"
            value={gesture}
            onChange={(e) => setGesture(e.target.value.toUpperCase().replace(/\s+/g, '_'))}
            className="w-full bg-black border border-white/20 text-white font-mono text-xs px-3 py-2 focus:border-matrix focus:outline-none"
          />
        </div>
        <div className="md:col-span-2">
          <input
            type="text"
            placeholder="Meaning (e.g. Yes / Agree)"
            value={meaning}
            onChange={(e) => setMeaning(e.target.value)}
            className="w-full bg-black border border-white/20 text-white font-mono text-xs px-3 py-2 focus:border-matrix focus:outline-none"
          />
        </div>
        <div className="md:col-span-1">
          <motion.button
            onClick={handleSave}
            disabled={status === 'saving' || !gesture || !meaning}
            className="w-full h-full flex items-center justify-center gap-2 bg-matrix/20 text-matrix border border-matrix/50 text-xs font-bold uppercase hover:bg-matrix hover:text-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
          >
            <Save size={14} />
            ADD
          </motion.button>
        </div>
      </div>

      {/* Status Feedback */}
      {status !== 'idle' && (
        <div className="flex items-center gap-2 mb-4 text-xs font-mono">
          {status === 'saving' && <span className="text-yellow-400 animate-pulse">PROCESSING...</span>}
          {status === 'saved_online' && <><CheckCircle size={14} className="text-matrix" /><span className="text-matrix">Saved to Cloud</span></>}
          {status === 'saved_offline' && <><AlertTriangle size={14} className="text-yellow-400" /><span className="text-yellow-400">Preserved to Edge (IndexedDB). Awaiting Sync.</span></>}
          {status === 'error' && <><AlertTriangle size={14} className="text-red-400" /><span className="text-red-400">Error preserving state.</span></>}
        </div>
      )}

      {/* Local Edge Cache View */}
      {savedDialects.length > 0 && (
        <div className="mt-6 border-t border-white/10 pt-4">
          <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-3">Edge Cached Mappings</div>
          <div className="max-h-40 overflow-y-auto scrollbar-thin">
            {savedDialects.map((d, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                <div className="flex items-center gap-4">
                  <span className="text-xs text-matrix font-mono">{d.gesture_sequence}</span>
                  <span className="text-[10px] text-gray-600">→</span>
                  <span className="text-xs text-white">{d.meaning}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
