export interface AuthPin {
  id: string;
  code: string;
}

export interface PlexUser {
  username: string;
  thumb: string;
}

export interface PlexConnection {
  uri: string;
  address: string;
  port: number;
  local: boolean;
  relay: boolean;
}

export interface PlexServer {
  name: string;
  sourceTitle: string | null;
  publicAddress: string;
  accessToken: string;
  relay: boolean;
  owned: boolean;
  httpsRequired: boolean;
  connections: PlexConnection[];
  provides?: string;
}
