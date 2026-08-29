import { FC, useState } from 'react';
import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import { manageLogin } from '@/services/ManageService.tsx';

interface Props {
  onAuthed: () => void;
  title?: string;
  description?: string;
  submitLabel?: string;
  /** Unlock action; defaults to the admin (manage) login. */
  submit?: (password: string) => Promise<void>;
}

const ManageGate: FC<Props> = ({
  onAuthed,
  title = 'This Configure page is protected',
  description = 'Enter the manage password to configure this addon.',
  submitLabel = 'Manage password',
  submit = manageLogin,
}) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const run = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await submit(password);
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
        <h1 className="text-xl font-bold">{title}</h1>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void run();
        }}
        className="space-y-3"
      >
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={submitLabel}
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
