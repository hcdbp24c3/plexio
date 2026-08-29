import { FC, useCallback, useEffect, useState } from 'react';
import ManageGate from '@/components/manageGate.tsx';
import Loading from '@/components/loading.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Switch } from '@/components/ui/switch.tsx';
import { Toaster } from '@/components/ui/toaster.tsx';
import { useToast } from '@/hooks/useToast';
import { useManageStatus } from '@/hooks/useManageStatus.ts';
import {
  changeManagePassword,
  deleteManageConfig,
  listManageConfigs,
  ManageConfigItem,
  manageLogout,
  saveManageSettings,
  setManagePassword,
} from '@/services/ManageService.tsx';

const SectionCard: FC<{ title: string; children: React.ReactNode }> = ({
  title,
  children,
}) => (
  <div className="border rounded-lg p-5 space-y-4">
    <h2 className="text-lg font-semibold">{title}</h2>
    {children}
  </div>
);

const AdminPage: FC = () => {
  const { toast } = useToast();
  const { status, loading, refresh } = useManageStatus();

  const [proxyEnabled, setProxyEnabled] = useState(true);
  const [proxyAdminOnly, setProxyAdminOnly] = useState(true);
  const [savingSettings, setSavingSettings] = useState(false);

  const [passwordConfigured, setPasswordConfigured] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordBusy, setPasswordBusy] = useState(false);

  const [configs, setConfigs] = useState<ManageConfigItem[]>([]);
  const [configsLoading, setConfigsLoading] = useState(false);

  useEffect(() => {
    if (!status) return;
    setProxyEnabled(status.proxyEnabled);
    setProxyAdminOnly(status.proxyAdminOnly);
    setPasswordConfigured(status.passwordRequired);
  }, [status]);

  const loadConfigs = useCallback(async () => {
    if (!status?.admin) return;
    setConfigsLoading(true);
    try {
      setConfigs(await listManageConfigs());
    } catch {
      toast({ title: 'Could not load installations', variant: 'destructive' });
    } finally {
      setConfigsLoading(false);
    }
  }, [status?.admin, toast]);

  useEffect(() => {
    void loadConfigs();
  }, [loadConfigs]);

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <Loading />
      </div>
    );
  }

  const admin = status?.admin ?? false;

  const saveSettings = async () => {
    setSavingSettings(true);
    try {
      await saveManageSettings({ proxyEnabled, proxyAdminOnly });
      toast({ title: 'Settings saved' });
    } catch {
      toast({ title: 'Could not save settings', variant: 'destructive' });
    } finally {
      setSavingSettings(false);
    }
  };

  const submitPassword = async () => {
    setPasswordBusy(true);
    try {
      if (passwordConfigured) {
        await changeManagePassword(currentPassword, newPassword);
      } else {
        await setManagePassword(newPassword);
      }
      setCurrentPassword('');
      setNewPassword('');
      toast({ title: 'Password updated' });
      await refresh();
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast({
        title: 'Could not update password',
        description: typeof detail === 'string' ? detail : undefined,
        variant: 'destructive',
      });
    } finally {
      setPasswordBusy(false);
    }
  };

  const removeConfig = async (id: string) => {
    try {
      await deleteManageConfig(id);
      setConfigs((items) => items.filter((item) => item.id !== id));
      toast({ title: 'Installation removed' });
    } catch {
      toast({
        title: 'Could not remove installation',
        variant: 'destructive',
      });
    }
  };

  const logout = async () => {
    await manageLogout();
    await refresh();
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Toaster />
      <div className="flex h-12 items-center justify-between">
        <h1 className="text-xl font-bold">Plexio admin</h1>
        {admin && (
          <Button onClick={() => void logout()} variant="ghost" size="sm">
            Lock
          </Button>
        )}
      </div>

      {status?.passwordRequired && !admin ? (
        <ManageGate onAuthed={() => void refresh()} />
      ) : (
        <>
          <SectionCard title="Server settings">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="proxyEnabled">Stream proxy</Label>
                <p className="text-sm text-muted-foreground">
                  Server-wide relay for streams and posters. When off, every
                  proxy request is refused regardless of addon config.
                </p>
              </div>
              <Switch
                id="proxyEnabled"
                checked={proxyEnabled}
                onCheckedChange={setProxyEnabled}
              />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="proxyAdminOnly">Admin-only proxy toggle</Label>
                <p className="text-sm text-muted-foreground">
                  Only admin sessions may turn the relay on from the Configure
                  page.
                </p>
              </div>
              <Switch
                id="proxyAdminOnly"
                checked={proxyAdminOnly}
                onCheckedChange={setProxyAdminOnly}
              />
            </div>
            <Button onClick={() => void saveSettings()} disabled={savingSettings}>
              {savingSettings ? 'Saving…' : 'Save settings'}
            </Button>
          </SectionCard>

          <SectionCard title="Manage password">
            <div className="space-y-3">
              {passwordConfigured && (
                <div className="space-y-1">
                  <Label htmlFor="currentPassword">Current password</Label>
                  <Input
                    id="currentPassword"
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                  />
                </div>
              )}
              <div className="space-y-1">
                <Label htmlFor="newPassword">
                  {passwordConfigured ? 'New password' : 'Set a password'}
                </Label>
                <Input
                  id="newPassword"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="At least 8 characters"
                />
              </div>
              <Button
                onClick={() => void submitPassword()}
                disabled={passwordBusy || newPassword.length < 8}
              >
                {passwordBusy
                  ? 'Saving…'
                  : passwordConfigured
                    ? 'Change password'
                    : 'Set password'}
              </Button>
              <p className="text-sm text-muted-foreground">
                {passwordConfigured
                  ? 'Protects the Configure page and this admin page.'
                  : 'No password is set yet. Setting one locks both the Configure page and this page behind a login.'}
              </p>
            </div>
          </SectionCard>

          <SectionCard title="Installations">
            <div className="space-y-2">
              {configsLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : configs.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No installations recorded yet. Configs are recorded here
                  whenever an admin saves the Configure page.
                </p>
              ) : (
                configs.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{item.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {item.serverCount} server
                        {item.serverCount === 1 ? '' : 's'} ·{' '}
                        {new Date(item.createdAt * 1000).toLocaleDateString()}
                      </p>
                    </div>
                    <Button
                      onClick={() => void removeConfig(item.id)}
                      variant="ghost"
                      size="sm"
                    >
                      Remove
                    </Button>
                  </div>
                ))
              )}
            </div>
          </SectionCard>
        </>
      )}
    </div>
  );
};

export default AdminPage;
