import { useMemo } from 'react';

/**
 * Extract the raw config token from an install/edit URL of the shape
 * `/{installationId}/{base64Config}/configure`. Used to scope the per-config
 * access password. Returns null on a fresh configure page.
 */
export const useConfigToken = (): string | null => {
  return useMemo(() => {
    const match = window.location.pathname.match(
      /^\/[^/]+\/([^/]+)\/(?:configure)?\/?$/,
    );
    return match ? match[1] : null;
  }, []);
};
