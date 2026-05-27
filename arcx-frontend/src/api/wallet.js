import client from './client';

/**
 * Fetch the authenticated user's wallet balance and metadata.
 * @returns {Promise<object>}
 */
export async function getBalance() {
  try {
    const { data } = await client.get('/api/v1/wallet/');
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

/**
 * Deposit INR into the wallet.
 * Includes an Idempotency-Key header to prevent duplicate processing.
 * @param {string} amount_inr — monetary value as a string (e.g. "500.00")
 * @param {string} pin — 6-digit transaction PIN
 * @returns {Promise<object>}
 */
export async function deposit(amount_inr, pin) {
  try {
    const { data } = await client.post(
      '/api/v1/wallet/deposit',
      { amount_inr, pin },
      { headers: { 'Idempotency-Key': crypto.randomUUID() } },
    );
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

/**
 * Withdraw ARCX tokens from the wallet.
 * Includes an Idempotency-Key header to prevent duplicate processing.
 * @param {string} amount_arcx — token quantity as a string (e.g. "10.5000")
 * @param {string} pin — 6-digit transaction PIN
 * @returns {Promise<object>}
 */
export async function withdraw(amount_arcx, pin) {
  try {
    const { data } = await client.post(
      '/api/v1/wallet/withdraw',
      { amount_arcx, pin },
      { headers: { 'Idempotency-Key': crypto.randomUUID() } },
    );
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

/**
 * Fetch paginated wallet transaction history.
 * @param {number} [limit=20] — number of records to return
 * @returns {Promise<object>}
 */
export async function getHistory(limit = 20) {
  try {
    const { data } = await client.get('/api/v1/wallet/history', {
      params: { limit },
    });
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

export async function transfer(payload, idempotencyKey) {
  try {
    const { data } = await client.post('/api/v1/transfer/', payload, {
      headers: { 'Idempotency-Key': idempotencyKey || crypto.randomUUID() },
    });
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}
