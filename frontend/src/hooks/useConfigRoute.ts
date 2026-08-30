import { useMemo } from 'react';

export interface ConfigRoute {
  /** Installation id — the first URL segment, stable across config edits. */
  id: string;
  /** Raw base64 config token from the install URL. */
  token: string;
}

/**
 * Read the installation id + config token from a setup URL of the shape
 * `/{installationId}/{base64Config}/configure`. Returns null on a fresh
 * configure page.
 */
export const useConfigRoute = (): ConfigRoute | null => {
  return useMemo(() => {
    const match = window.location.pathname.match(
      /^\/([^/]+)\/([^/]+)\/(?:configure)?\/?$/,
    );
    return match ? { id: match[1], token: match[2] } : null;
  }, []);
};
