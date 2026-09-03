import { BrowserRouter, Navigate, Routes, Route } from 'react-router-dom';
import usePlexToken from '@/hooks/usePlexToken.tsx';
import usePlexUser from '@/hooks/usePlexUser.tsx';
import { derivePlexUid } from '@/hooks/usePlexUid.ts';
import AdminPage from '@/pages/AdminPage.tsx';
import AuthRedirectPage from '@/pages/AuthRedirectPage.tsx';
import ProtectedFormPage from '@/pages/ProtectedFormPage.tsx';

function App() {
  const [token, setToken] = usePlexToken();
  const plexUser = usePlexUser(token);
  const uid = derivePlexUid(plexUser);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/auth-redirect"
          element={<AuthRedirectPage setPlexToken={setToken} />}
        ></Route>
        <Route path="/admin" element={<AdminPage />}></Route>
        <Route
          path="/u/:uid/*"
          element={
            <ProtectedFormPage plexToken={token} setPlexToken={setToken} />
          }
        ></Route>
        <Route
          path="/u/:uid"
          element={
            <ProtectedFormPage plexToken={token} setPlexToken={setToken} />
          }
        ></Route>
        <Route
          path="/*"
          element={
            uid ? (
              <Navigate to={`/u/${uid}`} replace />
            ) : (
              <ProtectedFormPage plexToken={token} setPlexToken={setToken} />
            )
          }
        ></Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
