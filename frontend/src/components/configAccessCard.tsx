import { FC, useState } from 'react';
import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { useToast } from '@/hooks/useToast';
import { setConfigAccessPassword } from '@/services/ManageService.tsx';

interface Props {
  token: string;
  passwordRequired: boolean;
  /** Whether the session holds an admin cookie (can reset the lock). */
  admin: boolean;
  onChanged: (passwordRequired: boolean) => void;
}

const ConfigAccessCard: FC<Props> = ({
  token,
  passwordRequired,
  admin,
  onChanged,
}) => {
  const { toast } = useToast();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [busy, setBusy] = useState(false);

  const errorMessage = (error: unknown): string | undefined => {
    const detail = (error as { response?: { data?: { detail?: string } } })
      ?.response?.data?.detail;
    return typeof detail === 'string' ? detail : undefined;
  };

  const save = async (password: string) => {
    setBusy(true);
    try {
      const locked = await setConfigAccessPassword(
        token,
        password,
        admin ? undefined : currentPassword || undefined,
      );
      setCurrentPassword('');
      setNewPassword('');
      onChanged(locked);
      toast({
        title: password
          ? 'Configuration password updated'
          : 'Configuration password removed',
      });
    } catch (error) {
      toast({
        title: 'Could not update configuration password',
        description: errorMessage(error),
        variant: 'destructive',
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="border rounded-lg p-5 space-y-4">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">Configuration password</h2>
        <p className="text-sm text-muted-foreground">
          {passwordRequired
            ? 'This configuration is protected: visitors must enter this password before they can edit it.'
            : 'No password set — anyone with this install link can edit the configuration. Set one to lock it.'}
        </p>
      </div>
      <div className="space-y-3">
        {passwordRequired && !admin && (
          <div className="space-y-1">
            <Label htmlFor="accessCurrent">Current password</Label>
            <Input
              id="accessCurrent"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Required to change or remove"
            />
          </div>
        )}
        <div className="space-y-1">
          <Label htmlFor="accessNew">
            {passwordRequired ? 'New password' : 'Password'}
          </Label>
          <Input
            id="accessNew"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Leave empty to remove protection"
          />
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => void save(newPassword)}
            disabled={busy || !newPassword}
          >
            {busy ? 'Saving…' : passwordRequired ? 'Change' : 'Protect'}
          </Button>
          {passwordRequired && (
            <Button
              onClick={() => void save('')}
              disabled={busy || (!admin && !currentPassword)}
              variant="ghost"
            >
              Remove password
            </Button>
          )}
        </div>
        {!passwordRequired && (
          <p className="text-sm text-muted-foreground">
            The server admin can always reset a lost password from this card.
          </p>
        )}
      </div>
    </div>
  );
};

export default ConfigAccessCard;
