import { FC, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Loading from '@/components/loading.tsx';
import useClientIdentifier from '@/hooks/useClientIdentifier.tsx';
import { SetPlexToken } from '@/hooks/usePlexToken.tsx';
import { derivePlexUid } from '@/hooks/usePlexUid.ts';
import { getAuthToken, getPlexUser } from '@/services/PlexService.tsx';

interface Props {
  setPlexToken: SetPlexToken;
}

const AuthRedirectPage: FC<Props> = ({ setPlexToken }) => {
  const [searchParams] = useSearchParams();
  const clientIdentifier = useClientIdentifier();
  const navigate = useNavigate();

  useEffect(() => {
    if (!clientIdentifier) return;

    const { id, code, redirect } = Object.fromEntries(searchParams.entries());

    const handleAuth = async (): Promise<void> => {
      const authToken = await getAuthToken(
        { id: id, code: code },
        clientIdentifier,
      );
      setPlexToken(authToken);

      const target = redirect || '/';

      if (target === '/' || target === '') {
        try {
          const user = await getPlexUser(authToken, clientIdentifier);
          const uid = derivePlexUid(user);
          navigate(uid ? `/u/${uid}` : target, { replace: true });
        } catch {
          navigate(target, { replace: true });
        }
      } else {
        navigate(target, { replace: true });
      }
    };

    void handleAuth();
  }, [searchParams, clientIdentifier, navigate, setPlexToken]);

  return <Loading />;
};

export default AuthRedirectPage;
