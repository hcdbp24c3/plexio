import { FC } from 'react';
import ConfigurationForm from '@/components/configurationForm';
import Loading from '@/components/loading.tsx';
import Login from '@/components/login.tsx';
import usePlexServers from '@/hooks/usePlexServers.tsx';
import { PlexUser } from '@/types/plex.tsx';

interface Props {
  plexToken: string | null;
  plexUser: PlexUser | null | undefined;
}

const NoServersMessage: FC = () => (
  <div className="border rounded-lg p-6 text-center space-y-2">
    <h2 className="text-lg font-semibold">No Plex servers found</h2>
    <p className="text-sm text-muted-foreground">
      This Plex account does not own or have access to any Plex Media
      Servers. Make sure your server is signed in to this account, or ask
      the server owner to share it with you.
    </p>
  </div>
);

const ProtectedForm: FC<Props> = ({ plexToken, plexUser }) => {
  const { servers, ready } = usePlexServers(plexToken);

  if (plexUser === null) {
    return <Login />;
  }

  if (plexUser === undefined || !ready) {
    return <Loading />;
  }

  if (!servers.length) {
    return <NoServersMessage />;
  }

  return <ConfigurationForm servers={servers} />;
};

export default ProtectedForm;
