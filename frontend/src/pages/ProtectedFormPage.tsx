import { FC } from 'react';
import ConfigAccessCard from '@/components/configAccessCard.tsx';
import FAQ from '@/components/faq.tsx';
import Header from '@/components/header.tsx';
import Loading from '@/components/loading.tsx';
import ManageGate from '@/components/manageGate.tsx';
import ProtectedForm from '@/components/protectedForm.tsx';
import { Toaster } from '@/components/ui/toaster.tsx';
import { useConfigAccess } from '@/hooks/useConfigAccess.ts';
import { useConfigToken } from '@/hooks/useConfigToken.ts';
import { useManageStatus } from '@/hooks/useManageStatus.ts';
import usePlexUser from '@/hooks/usePlexUser.tsx';
import { configAccessLogin } from '@/services/ManageService.tsx';

interface Props {
  plexToken: string | null;
  setPlexToken: (token: string | null) => void;
}

const ProtectedFormPage: FC<Props> = ({ plexToken, setPlexToken }) => {
  const plexUser = usePlexUser(plexToken);
  const configToken = useConfigToken();
  const { status: manageStatus, loading: manageLoading } = useManageStatus();
  const {
    status: accessStatus,
    loading: accessLoading,
    refresh: refreshAccess,
  } = useConfigAccess(configToken);

  if (manageLoading || accessLoading) {
    return (
      <div className="mx-auto max-w-2xl">
        <Header plexUser={plexUser} setPlexToken={setPlexToken} />
        <Loading />
      </div>
    );
  }

  const configLocked =
    !!configToken &&
    accessStatus?.passwordRequired === true &&
    accessStatus?.unlocked === false;

  return (
    <div className="mx-auto max-w-2xl">
      <Toaster />
      <Header plexUser={plexUser} setPlexToken={setPlexToken} />
      {configLocked && configToken ? (
        <ManageGate
          onAuthed={() => void refreshAccess()}
          title="This configuration is protected"
          description="Enter this configuration's password to edit it."
          submitLabel="Configuration password"
          submit={(password) => configAccessLogin(configToken, password)}
        />
      ) : (
        <>
          <ProtectedForm
            plexToken={plexToken}
            plexUser={plexUser}
            manageStatus={manageStatus}
          />
          {configToken && (
            <div className="mt-4">
              <ConfigAccessCard
                token={configToken}
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
