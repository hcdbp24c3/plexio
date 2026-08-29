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
