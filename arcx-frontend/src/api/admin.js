import api from './client';

export const getUsers = async () => {
  const response = await api.get('/admin/users');
  return response.data;
};

export const getPendingKYC = async () => {
  const response = await api.get('/admin/kyc');
  return response.data;
};

export const updateKYCStatus = async (recordId, action) => {
  const response = await api.post('/admin/kyc', {
    record_id: recordId,
    action: action, // 'approve' or 'reject'
  });
  return response.data;
};

export const computeNAV = async () => {
  const response = await api.post('/admin/nav/compute');
  return response.data;
};
