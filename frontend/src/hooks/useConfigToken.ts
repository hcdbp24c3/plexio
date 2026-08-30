import { useConfigRoute } from '@/hooks/useConfigRoute.ts';

/**
 * Extract the raw config token from an install/edit URL of the shape
 * `/{installationId}/{base64Config}/configure`. Returns null on a fresh
 * configure page.
 */
export const useConfigToken = (): string | null => {
  return useConfigRoute()?.token ?? null;
};
