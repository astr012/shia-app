'use client';

import { useState, useCallback, useEffect } from 'react';

/**
 * useDatabaseFailover 
 * Implement an IndexedDB failover mechanism for UI actions (e.g. saving custom dictionaries).
 * Falls back to saving locally if the backend PostgreSQL encounters an outage (HTTP 503/Fetch Error).
 */
export function useDatabaseFailover() {
  const [dbInstance, setDbInstance] = useState<IDBDatabase | null>(null);

  useEffect(() => {
    // Initialize standard IndexedDB
    const request = indexedDB.open('SignAIDatabase', 1);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('offline_sync_queue')) {
        db.createObjectStore('offline_sync_queue', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('dialect_profiles')) {
        db.createObjectStore('dialect_profiles', { keyPath: 'user_id' });
      }
    };

    request.onsuccess = (event) => {
      setDbInstance((event.target as IDBOpenDBRequest).result);
    };

    request.onerror = (event) => {
      console.error('[IndexedDB] Failover initialization error:', event);
    };
  }, []);

  const saveOfflineAction = useCallback((endpoint: string, payload: any) => {
    if (!dbInstance) return;
    
    return new Promise((resolve, reject) => {
      const transaction = dbInstance.transaction(['offline_sync_queue'], 'readwrite');
      const store = transaction.objectStore('offline_sync_queue');
      
      const request = store.add({
        endpoint,
        payload,
        timestamp: Date.now(),
        status: 'pending'
      });

      request.onsuccess = () => resolve(true);
      request.onerror = (e) => reject(e);
    });
  }, [dbInstance]);

  const attemptResync = useCallback(async () => {
    if (!dbInstance) return;

    const transaction = dbInstance.transaction(['offline_sync_queue'], 'readwrite');
    const store = transaction.objectStore('offline_sync_queue');
    const request = store.getAll();

    request.onsuccess = async () => {
      const pendingItems = request.result;
      for (const item of pendingItems) {
        try {
          // Attempt the fetch call again
          const res = await fetch(item.endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item.payload)
          });
          
          if (res.ok) {
            // Remove from queue upon success
            const delTx = dbInstance.transaction(['offline_sync_queue'], 'readwrite');
            delTx.objectStore('offline_sync_queue').delete(item.id);
          }
        } catch (e) {
          console.warn(`[Sync] Resync failed for ID ${item.id}. Keeping in failover queue.`);
        }
      }
    };
  }, [dbInstance]);

  const saveDialectProfileOffline = useCallback((userId: string | number, profileData: any) => {
    if (!dbInstance) return;
    
    return new Promise((resolve, reject) => {
      const transaction = dbInstance.transaction(['dialect_profiles'], 'readwrite');
      const store = transaction.objectStore('dialect_profiles');
      
      const request = store.put({
        user_id: userId,
        profile: profileData,
        last_synced: Date.now()
      });

      request.onsuccess = () => resolve(true);
      request.onerror = (e) => reject(e);
    });
  }, [dbInstance]);

  const getDialectProfileOffline = useCallback((userId: string | number) => {
    if (!dbInstance) return Promise.resolve(null);
    
    return new Promise((resolve, reject) => {
      const transaction = dbInstance.transaction(['dialect_profiles'], 'readonly');
      const store = transaction.objectStore('dialect_profiles');
      const request = store.get(userId);

      request.onsuccess = () => {
        resolve(request.result?.profile || null);
      };
      request.onerror = (e) => reject(e);
    });
  }, [dbInstance]);

  return { saveOfflineAction, attemptResync, saveDialectProfileOffline, getDialectProfileOffline };
}
