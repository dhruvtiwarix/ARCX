import client from './client';

/**
 * Fetch the full portfolio analytics for the authenticated user.
 * Returns holdings snapshot, P&L series, yield earned, and tx breakdown.
 */
export async function getAnalytics() {
  try {
    const { data } = await client.get('/api/v1/portfolio/analytics');
    return data;
  } catch (error) {
    throw error.response?.data || error;
  }
}
