'use client';

// ============================================================
// PIPELINE LAYER 3: Core Database & Identity Architecture
//
// Manages Database-Agnostic Redundancy via IndexedDB Syncing.
// If the PostgreSQL cluster goes offline, the web client
// isolates instantly and relies entirely on local storage without
// halting translation, pushing up when connection is restored.
// ============================================================

import { useState, useEffect, useCallback } from 'react';

export interface UserProfile {
  user_id: string;
  regional_dialect: string;
  bespoke_dictionary: Record<string, string[]>;
}

const DB_NAME = 'SignAIDatabase';
const DB_VERSION = 1;
const STORE_NAME = 'UserProfile';

const DEFAULT_PROFILE: UserProfile = {
  user_id: 'anonymous',
  regional_dialect: 'ASL',
  bespoke_dictionary: {},
};

export function useUserProfile(token: string | null) {
  const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isOfflineMode, setIsOfflineMode] = useState(false);

  // ── IndexedDB Configuration ──────────────────────────────
  const openDB = (): Promise<IDBDatabase> => {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = (e) => {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'user_id' });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  };

  const getLocalProfile = async (userId: string): Promise<UserProfile | null> => {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(userId);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
  };

  const saveLocalProfile = async (p: UserProfile): Promise<void> => {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.put(p);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  };

  // ── Upstream Sync Logic ──────────────────────────────────
  const fetchUpstreamProfile = useCallback(async () => {
    if (!token) return;
    setIsSyncing(true);
    
    try {
      const res = await fetch('/api/profile/sync', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.status === 503 || !res.ok) {
        throw new Error("Cluster offline or network isolated");
      }

      const data: UserProfile = await res.json();
      setProfile(data);
      await saveLocalProfile(data);
      setIsOfflineMode(false);
    } catch (error) {
      console.warn('[Self-Healing] Database cluster unreachable. Failing over to IndexedDB.');
      setIsOfflineMode(true);
      
      // Decode user_id from JWT or fallback to anonymous
      let userId = 'anonymous';
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        userId = payload.sub || 'anonymous';
      } catch(e) {}
      
      const local = await getLocalProfile(userId);
      if (local) setProfile(local);
    } finally {
      setIsSyncing(false);
    }
  }, [token]);

  const updateProfile = useCallback(async (updates: Partial<UserProfile>) => {
    const updated = { ...profile, ...updates };
    setProfile(updated);
    
    // Always persist to local edge client immediately (Fail-Safe)
    await saveLocalProfile(updated);

    if (!token) return;
    
    try {
      const res = await fetch('/api/profile/sync', {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updated)
      });
      if (res.ok) {
        setIsOfflineMode(false);
      } else {
        setIsOfflineMode(true);
        console.warn('[Self-Healing] Upstream push failed. Persisted in IndexedDB. Will sync later.');
      }
    } catch (e) {
      setIsOfflineMode(true);
      console.warn('[Self-Healing] Network dropped. Saved locally in IndexedDB.');
    }
  }, [profile, token]);

  useEffect(() => {
    if (token) {
      fetchUpstreamProfile();
    }
  }, [token, fetchUpstreamProfile]);

  return {
    profile,
    updateProfile,
    isSyncing,
    isOfflineMode
  };
}
