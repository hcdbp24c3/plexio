import { useCallback, useEffect, useState } from 'react';
import {
  ConfigAccessStatus,
  getConfigAccessStatus,
} from '@/services/ManageService.tsx';

export const useConfigAccess = (token: string | null) => {
  const [status, setStatus] = useState<ConfigAccessStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!token) {
      setStatus(null);
      setLoading(false);
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

  return { status, loading, refresh };
};
