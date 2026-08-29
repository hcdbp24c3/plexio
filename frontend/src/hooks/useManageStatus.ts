import { useCallback, useEffect, useState } from 'react';
import {
  getManageStatus,
  ManageStatus,
} from '@/services/ManageService.tsx';

export const useManageStatus = () => {
  const [status, setStatus] = useState<ManageStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getManageStatus();
      setStatus(data);
    } catch (error) {
      console.error('Error fetching manage status:', error);
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { status, loading, refresh };
};
