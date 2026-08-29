import { BrowserRouter, Routes, Route } from 'react-router-dom';
import usePlexToken from '@/hooks/usePlexToken.tsx';
import AdminPage from '@/pages/AdminPage.tsx';
import AuthRedirectPage from '@/pages/AuthRedirectPage.tsx';
import ProtectedFormPage from '@/pages/ProtectedFormPage.tsx';

function App() {
  const [token, setToken] = usePlexToken();

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/auth-redirect"
          element={<AuthRedirectPage setPlexToken={setToken} />}
        ></Route>
        <Route path="/admin" element={<AdminPage />}></Route>
        <Route
          path="/*"
          element={
            <ProtectedFormPage plexToken={token} setPlexToken={setToken} />
          }
        ></Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
