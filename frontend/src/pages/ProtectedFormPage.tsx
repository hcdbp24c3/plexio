import { FC } from 'react';
import FAQ from '@/components/faq.tsx';
import Header from '@/components/header.tsx';
import Loading from '@/components/loading.tsx';
import ManageGate from '@/components/manageGate.tsx';
import ProtectedForm from '@/components/protectedForm.tsx';
import { Toaster } from '@/components/ui/toaster.tsx';
import { useManageStatus } from '@/hooks/useManageStatus.ts';
import usePlexUser from '@/hooks/usePlexUser.tsx';

interface Props {
  plexToken: string | null;
  setPlexToken: (token: string | null) => void;
}

const ProtectedFormPage: FC<Props> = ({ plexToken, setPlexToken }) => {
  const plexUser = usePlexUser(plexToken);
  const { status, loading, refresh } = useManageStatus();

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl">
        <Header plexUser={plexUser} setPlexToken={setPlexToken} />
        <Loading />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Toaster />
      <Header plexUser={plexUser} setPlexToken={setPlexToken} />
      {status?.passwordRequired && !status.admin ? (
        <ManageGate onAuthed={() => void refresh()} />
      ) : (
        <ProtectedForm
          plexToken={plexToken}
          plexUser={plexUser}
          manageStatus={status}
        />
      )}
      <FAQ />
    </div>
  );
};

export default ProtectedFormPage;
