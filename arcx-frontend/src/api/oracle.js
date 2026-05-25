import client from './client';

/**
 * Fetch the current live ARCX token price.
 * Public endpoint — no authentication required.
 * @returns {Promise<object>}
 */
export async function getLivePrice() {
  try {
    const { data } = await client.get('/api/v1/oracle/price');
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

/**
 * Fetch historical NAV data for charting.
 * Public endpoint — no authentication required.
 * @param {number} [days=30] — number of days of history to retrieve
 * @returns {Promise<object>}
 */
export async function getNAVHistory(days = 30) {
  try {
    const { data } = await client.get('/api/v1/nav/history', {
      params: { days },
    });
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}

/**
 * Fetch today's published NAV value.
 * Public endpoint — no authentication required.
 * @returns {Promise<object>}
 */
export async function getTodayNAV() {
  try {
    const { data } = await client.get('/api/v1/nav/today');
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}
