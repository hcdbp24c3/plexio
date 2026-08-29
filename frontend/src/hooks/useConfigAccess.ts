import { useCallback, useEffect, useState } from 'react';
import {
  ConfigAccessStatus,
  getConfigAccessStatus,
} from '@/services/ManageService.tsx';

/**
 * Per-config unlock is stateless: the backend validates the password once per
 * page load and keeps no cookie, so `unlocked` lives only in React state and
 * resets on every reload (F5) — matching the reference fork.
 */
export const useConfigAccess = (token: string | null) => {
  const [status, setStatus] = useState<ConfigAccessStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [unlocked, setUnlocked] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) {
      setStatus(null);
      setLoading(false);
      setUnlocked(false);
      return;
    }
    setLoading(true);
    try {
      setStatus(await getConfigAccessStatus(token));
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const unlock = useCallback(() => setUnlocked(true), []);

  const locked = !!token && status?.passwordRequired === true && !unlocked;

  return { status, loading, locked, unlock, refresh };
};
