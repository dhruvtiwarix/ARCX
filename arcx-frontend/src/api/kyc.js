import client from './client';

/**
 * Submit a KYC verification request.
 * @param {{tier: string, document_type: string, document_ref: string}} payload
 * @returns {Promise<object>}
 */
export async function submitKYC(payload) {
  try {
    const { data } = await client.post('/api/v1/kyc/submit', {
      tier: payload.tier,
      document_type: payload.document_type,
      document_ref: payload.document_ref,
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
