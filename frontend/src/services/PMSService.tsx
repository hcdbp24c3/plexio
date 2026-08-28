import axios from 'axios';

export interface PlexSection {
  key: string;
  title: string;
  type: string;
}

export const isServerAliveLocal = async (serverUrl: string, token: string) => {
  try {
    const response = await axios.get(serverUrl, {
      timeout: 25000,
      params: {
        'X-Plex-Token': token,
      },
      headers: { Accept: 'application/json' },
    });
    return response.status === 200;
  } catch (error) {
    console.error('Error while ping PMS:', error);
    return false;
  }
};

export const getSections = async (
  serverUrl: string,
  token: string,
): Promise<PlexSection[]> => {
  try {
    // Sections are fetched through the addon backend so browsers are never
    // blocked by the Plex server's CORS policy (the backend must be able to
    // reach it anyway for catalogs/streams to work).
    const response = await axios.get<{ sections: PlexSection[] }>(
      `${window.location.origin}/api/v1/sections`,
      {
        timeout: 25000,
        params: {
          url: serverUrl,
          token: token,
        },
      },
    );

    return response.data?.sections ?? [];
  } catch (error) {
    console.error('Error fetching Plex sections:', error);
    throw error;
  }
};
