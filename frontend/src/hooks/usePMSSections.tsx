import { useEffect, useState } from 'react';
import { PlexToken } from '@/hooks/usePlexToken.tsx';
import { getSections, PlexSection } from '@/services/PMSService.tsx';

const usePMSSections = (
  serverUrl: string,
  plexToken: PlexToken,
): { sections: PlexSection[]; loading: boolean; error: string | null } => {
  const [sections, setSections] = useState<PlexSection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSections([]);
    setError(null);
    if (!plexToken || !serverUrl) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    const fetchSections = async (): Promise<void> => {
      try {
        const sectionsData = await getSections(serverUrl, plexToken);
        if (!cancelled) setSections(sectionsData);
      } catch (e) {
        if (!cancelled) {
          setError(
            'Could not load library sections from this URL. Make sure the server is reachable from the Plexio backend.',
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void fetchSections();
    return () => {
      cancelled = true;
    };
  }, [serverUrl, plexToken]);

  return { sections, loading, error };
};

export default usePMSSections;
