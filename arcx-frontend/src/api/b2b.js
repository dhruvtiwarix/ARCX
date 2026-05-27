import client from './client'

export const b2bApi = {
  setTransactionPin: async (current_pin, new_pin) => {
    // Note: the backend will be updated to accept both
    const { data } = await client.post('/api/v1/b2b/set-pin/', { current_pin, pin: new_pin })
    return data
  },

  setWebhookConfig: async (url, secret_key) => {
    const { data } = await client.post('/api/v1/b2b/webhooks/', { url, secret_key })
    return data
  },

  transfer: async (alias, amount_arcx, pin, idempotencyKey) => {
    const { data } = await client.post('/api/v1/b2b/transfer/', 
      { alias, amount_arcx, pin },
      { headers: { 'Idempotency-Key': idempotencyKey } }
    )
    return data
  },
}
