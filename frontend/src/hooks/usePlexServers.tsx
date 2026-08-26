import { useEffect, useState } from 'react';
import useClientIdentifier from '@/hooks/useClientIdentifier.tsx';
import { PlexToken } from '@/hooks/usePlexToken.tsx';
import { getPlexServers } from '@/services/PlexService.tsx';
import { PlexServer } from '@/types/plex.tsx';

const usePlexServers = (
  plexToken: PlexToken | null,
): { servers: PlexServer[]; ready: boolean } => {
  const [servers, setServers] = useState<PlexServer[]>([]);
  const [ready, setReady] = useState(false);
  const clientIdentifier = useClientIdentifier();

  useEffect(() => {
    if (!clientIdentifier || !plexToken) return;

    const fetchPlexServers = async (): Promise<void> => {
      try {
        const plexServers = await getPlexServers(plexToken, clientIdentifier);
        setServers(plexServers);
      } catch (error) {
        console.error('Error fetching Plex servers:', error);
      } finally {
        setReady(true);
      }
    };

    void fetchPlexServers();
  }, [clientIdentifier, plexToken]);

  return { servers, ready };
};

export default usePlexServers;
