import { useMemo } from 'react';
import { parseAddonUrl } from '@/components/configurationForm/utils.tsx';
import { ConfigurationFormType } from '@/components/configurationForm/formSchema.tsx';

/**
 * Read the config token from an install/edit URL of the shape
 * `/{installationId}/{base64Config}/configure` and parse it back into form
 * values, so opening an existing addon link pre-fills the Configure form.
 * Returns null for any other path (fresh configure page).
 */
export const useAddonConfigFromUrl = (): ConfigurationFormType | null => {
  return useMemo(() => {
    const match = window.location.pathname.match(
      /^\/[^/]+\/([^/]+)\/(?:configure)?\/?$/,
    );
    if (!match) return null;
    return parseAddonUrl(match[1]);
  }, []);
};
