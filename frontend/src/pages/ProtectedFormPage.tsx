import { FC } from 'react';
import ConfigAccessCard from '@/components/configAccessCard.tsx';
import FAQ from '@/components/faq.tsx';
import Header from '@/components/header.tsx';
import Loading from '@/components/loading.tsx';
import ManageGate from '@/components/manageGate.tsx';
import ProtectedForm from '@/components/protectedForm.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Toaster } from '@/components/ui/toaster.tsx';
import { useConfigAccess } from '@/hooks/useConfigAccess.ts';
import { useConfigRoute } from '@/hooks/useConfigRoute.ts';
import { useManageStatus } from '@/hooks/useManageStatus.ts';
import usePlexUser from '@/hooks/usePlexUser.tsx';
import { configAccessLogin } from '@/services/ManageService.tsx';

interface Props {
  plexToken: string | null;
  setPlexToken: (token: string | null) => void;
}

/**
 * The visitor's own setup page (`/u/<id>` resolves here). Shows the config
 * form plus — for a saved setup — the install link and the per-setup
 * password card. The setup id keys the lock, so it survives config edits.
 */
const ProtectedFormPage: FC<Props> = ({ plexToken, setPlexToken }) => {
  const plexUser = usePlexUser(plexToken);
  const configRoute = useConfigRoute();
  const { status: manageStatus, loading: manageLoading } = useManageStatus();
  const {
    status: accessStatus,
    loading: accessLoading,
    locked: configLocked,
    unlock: unlockConfig,
    refresh: refreshAccess,
  } = useConfigAccess(configRoute?.id ?? null);

  if (manageLoading || accessLoading) {
    return (
      <div className="mx-auto max-w-2xl">
        <Header plexUser={plexUser} setPlexToken={setPlexToken} />
        <Loading />
      </div>
    );
  }

  const installUrl = configRoute
    ? `${window.location.origin}/${configRoute.id}/${configRoute.token}/manifest.json`
    : null;

  const openInStremio = () => {
    if (installUrl) {
      window.location.href = installUrl.replace(/^https?:\/\//, 'stremio://');
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <Toaster />
      <Header plexUser={plexUser} setPlexToken={setPlexToken} />
      {configLocked && configRoute ? (
        <ManageGate
          onAuthed={unlockConfig}
          title="This configuration is protected"
          description="Enter this configuration's password to edit it."
          submitLabel="Configuration password"
          submit={(password) => configAccessLogin(configRoute.id, password)}
        />
      ) : (
        <>
          <ProtectedForm plexToken={plexToken} plexUser={plexUser} />
          {installUrl && (
            <div className="mt-4 space-y-2 rounded-lg border p-3">
              <h2 className="text-lg font-semibold">Your addon install link</h2>
              <p className="text-sm text-muted-foreground">
                Bookmark this page (<code>/u/{configRoute?.id}</code>) to come
                back and edit this setup. Anyone with this link can install it.
              </p>
              <div className="flex items-center space-x-2">
                <Button
                  type="button"
                  onClick={openInStremio}
                  className="h-9 rounded-md px-4"
                >
                  Open in Stremio
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="h-9 rounded-md px-4"
                  onClick={() => void navigator.clipboard.writeText(installUrl)}
                >
                  Copy link
                </Button>
              </div>
            </div>
          )}
          {configRoute && (
            <div className="mt-4">
              <ConfigAccessCard
                id={configRoute.id}
                passwordRequired={accessStatus?.passwordRequired ?? false}
                admin={manageStatus?.admin ?? false}
                onChanged={() => void refreshAccess()}
              />
            </div>
          )}
        </>
      )}
      <FAQ />
    </div>
  );
};

export default ProtectedFormPage;
