import { ConfigurationFormType } from '@/components/configurationForm/formSchema.tsx';

export const parseUrlToIpPort = (url: string): string => {
  const urlObj = new URL(url);

  const hostname = urlObj.hostname;
  const port = urlObj.port;

  const ipMatch = hostname.match(/^(\d+-\d+-\d+-\d+)/);
  if (!ipMatch) {
    throw new Error('Invalid hostname format.');
  }

  const ip = ipMatch[1].replace(/-/g, '.');

  return `${ip}:${port}`;
};

const decodeBase64Url = (input: string): string => {
  const base64 = input.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64.padEnd(
    base64.length + ((4 - (base64.length % 4)) % 4),
    '=',
  );
  const binary = atob(padded);
  try {
    return decodeURIComponent(
      binary
        .split('')
        .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join(''),
    );
  } catch {
    return binary;
  }
};

const toBool = (value: unknown, fallback: boolean): boolean =>
  typeof value === 'boolean' ? value : fallback;

const toSections = (value: unknown) => {
  if (!Array.isArray(value)) return [];
  const sections: unknown[] = value;
  return sections
    .filter((s): s is { key: string; title: string; type: string } => {
      if (!s || typeof s !== 'object') return false;
      const section = s as Record<string, unknown>;
      return (
        typeof section.key === 'string' &&
        typeof section.title === 'string' &&
        typeof section.type === 'string'
      );
    })
    .map((s) => ({ key: s.key, title: s.title, type: s.type }));
};

/** Turn a legacy (single-server) config into the multi-server shape. */
const legacyToServers = (cfg: Record<string, unknown>) => {
  if (!cfg.accessToken && !cfg.discoveryUrl && !cfg.streamingUrl) return [];
  return [
    {
      accessToken: String(cfg.accessToken ?? ''),
      discoveryUrl: String(cfg.discoveryUrl ?? ''),
      streamingUrl: String(cfg.streamingUrl ?? ''),
      serverName: String(cfg.serverName ?? 'My Plex'),
      sections: toSections(cfg.sections),
    },
  ];
};

/**
 * Parse an existing addon install URL (or a raw base64 config) back into
 * form values, so an old setup can be edited instead of rebuilt from scratch.
 * Supports the current multi-server payload as well as the legacy flat shape.
 */
export const parseAddonUrl = (input: string): ConfigurationFormType | null => {
  let token = input.trim();
  if (!token) return null;

  if (/^https?:\/\//i.test(token) || token.includes('/manifest.json')) {
    const match = token.match(/\/([^/]+)\/manifest\.json$/);
    if (!match) return null;
    token = match[1];
  }

  let raw: string;
  try {
    raw = decodeBase64Url(token);
  } catch {
    return null;
  }

  let cfg: unknown;
  try {
    cfg = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!cfg || typeof cfg !== 'object') return null;

  const config = cfg as Record<string, unknown>;
  const servers = Array.isArray(config.servers)
    ? (config.servers as Record<string, unknown>[])
    : legacyToServers(config);

  if (servers.length === 0) return null;

  return {
    selectedServers: servers.map((s) => String(s.serverName ?? '')),
    serverConfigs: servers.map((s) => ({
      serverName: String(s.serverName ?? ''),
      discoveryUrl: String(s.discoveryUrl ?? ''),
      streamingUrl: String(s.streamingUrl ?? ''),
      sections: toSections(s.sections),
    })),
    includeTranscodeOriginal: toBool(config.includeTranscodeOriginal, false),
    includeTranscodeDown: toBool(config.includeTranscodeDown, false),
    transcodeDownQualities: Array.isArray(config.transcodeDownQualities)
      ? (config.transcodeDownQualities as string[])
      : [],
    includeCatalogs: toBool(config.includeCatalogs, true),
    includePlexTv: toBool(config.includePlexTv, false),
    streamProxy: toBool(config.streamProxy, false),
  };
};
