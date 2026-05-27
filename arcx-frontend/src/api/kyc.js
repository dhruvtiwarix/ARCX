import client from './client';

/**
 * Submit a KYC verification request.
 * @param {{pan_number: string, pin: string}} payload
 * @returns {Promise<object>}
 */
export async function submitKYC(payload) {
  try {
    const { data } = await client.post('/api/v1/kyc/submit', {
      pan_number: payload.pan_number,
      pin: payload.pin,
    });
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

/**
 * Fetch the authenticated user's current KYC verification status.
 * @returns {Promise<object>}
 */
export async function getKYCStatus() {
  try {
    const { data } = await client.get('/api/v1/kyc/status');
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}
