import { useMemo } from 'react';

export interface ConfigRoute {
  /** Installation id — the first URL segment, stable across config edits. */
  id: string;
  /** Raw base64 config token from the install URL. Null when at /u/<uid> root. */
  token: string | null;
  /** Plex uid namespace. Null when legacy route. */
  uid: string | null;
  /** True when pathname === /u/<uid> or /u/<uid>/configure and no id/token. */
  isUserRoot: boolean;
}

/**
 * Read the installation id + config token from setup URLs.
 * Supports both legacy `/{id}/{token}/configure` and new `/u/:uid/{id}/{token}/configure`
 * plus user root `/u/:uid` or `/u/:uid/configure`.
 */
export const useConfigRoute = (): ConfigRoute | null => {
  return useMemo(() => {
    const pathname = window.location.pathname;

    const uFull = pathname.match(
      /^\/u\/([^/]+)\/([^/]+)\/([^/]+)(?:\/configure)?\/?$/,
    );
    if (uFull) {
      return {
        uid: uFull[1],
        id: uFull[2],
        token: uFull[3],
        isUserRoot: false,
      };
    }

    const uRoot = pathname.match(/^\/u\/([^/]+)\/?(?:configure)?\/?$/);
    if (uRoot) {
      const uid = uRoot[1];
      return {
        uid,
        id: uid,
        token: null,
        isUserRoot: true,
      };
    }

    const legacy = pathname.match(
      /^\/([^/]+)\/([^/]+)(?:\/configure)?\/?$/,
    );
    if (legacy) {
      if (legacy[1] === 'u') return null;
      return {
        uid: null,
        id: legacy[1],
        token: legacy[2],
        isUserRoot: false,
      };
    }

    return null;
  }, []);
};
