import { useMemo } from 'react';

import { PlexUser } from '@/types/plex';

export type PlexUid = string | null;

export const derivePlexUid = (
  user?: PlexUser | null | undefined,
): PlexUid => {
  if (!user) return null;
  if (user.id != null) return String(user.id);
  if (user.uuid) return user.uuid;
  if (user.username)
    return user.username
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  return null;
};

export const usePlexUid = (
  plexUser: PlexUser | null | undefined,
): PlexUid => useMemo(() => derivePlexUid(plexUser), [plexUser]);

export default usePlexUid;
