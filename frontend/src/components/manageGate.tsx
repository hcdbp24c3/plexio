import { FC, useState } from 'react';
import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import { manageLogin } from '@/services/ManageService.tsx';

interface Props {
  onAuthed: () => void;
}

const ManageGate: FC<Props> = ({ onAuthed }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await manageLogin(password);
      onAuthed();
    } catch {
      setError('Wrong password. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="border rounded-lg p-6 space-y-4">
      <div className="text-center space-y-1">
        <h1 className="text-xl font-bold">This Configure page is protected</h1>
        <p className="text-sm text-muted-foreground">
          Enter the manage password to configure this addon.
        </p>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
        className="space-y-3"
      >
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Manage password"
          autoFocus
          disabled={submitting}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? 'Checking…' : 'Unlock'}
        </Button>
      </form>
    </div>
  );
};

export default ManageGate;
