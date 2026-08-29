import axios from 'axios';

export interface ManageStatus {
  passwordRequired: boolean;
  admin: boolean;
  proxyEnabled: boolean;
  proxyAdminOnly: boolean;
}

export const getManageStatus = async (): Promise<ManageStatus> => {
  const response = await axios.get<ManageStatus>('/api/v1/manage/status');
  return response.data;
};

export const manageLogin = async (password: string): Promise<void> => {
  await axios.post('/api/v1/manage/login', { password });
};

export const manageLogout = async (): Promise<void> => {
  await axios.post('/api/v1/manage/logout');
};

export interface ManageSettings {
  proxyEnabled: boolean;
  proxyAdminOnly: boolean;
}

export const saveManageSettings = async (
  settings: ManageSettings,
): Promise<ManageSettings> => {
  const response = await axios.post<ManageSettings>(
    '/api/v1/manage/settings',
    settings,
  );
  return response.data;
};

export interface ManageConfigItem {
  id: string;
  name: string;
  serverCount: number;
  createdAt: number;
}

export const listManageConfigs = async (): Promise<ManageConfigItem[]> => {
  const response = await axios.get<ManageConfigItem[]>('/api/v1/manage/configs');
  return response.data;
};

export const deleteManageConfig = async (id: string): Promise<void> => {
  await axios.delete(`/api/v1/manage/configs/${id}`);
};

export const recordConfig = (config: Record<string, unknown>): void => {
  // keepalive survives the immediate navigation to the stremio:// install link.
  void fetch('/api/v1/manage/configs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config }),
    keepalive: true,
  }).catch(() => undefined);
};

export const setManagePassword = async (password: string): Promise<void> => {
  await axios.post('/api/v1/manage/password', { password });
};

export interface ConfigAccessStatus {
  passwordRequired: boolean;
}

export const getConfigAccessStatus = async (
  token: string,
): Promise<ConfigAccessStatus> => {
  const response = await axios.post<ConfigAccessStatus>(
    '/api/v1/access/status',
    { token },
  );
  return response.data;
};

/** Validates the config password for this page load; no session is kept. */
export const configAccessLogin = async (
  token: string,
  password: string,
): Promise<void> => {
  await axios.post('/api/v1/access/login', { token, password });
};

export const setConfigAccessPassword = async (
  token: string,
  password: string,
  currentPassword?: string,
): Promise<boolean> => {
  const response = await axios.post<{ passwordRequired: boolean }>(
    '/api/v1/access/password',
    { token, password, currentPassword },
  );
  return response.data.passwordRequired;
};

export const changeManagePassword = async (
  currentPassword: string,
  newPassword: string,
): Promise<void> => {
  await axios.post('/api/v1/manage/password/change', {
    currentPassword,
    newPassword,
  });
};
