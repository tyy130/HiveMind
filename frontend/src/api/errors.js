function extractDetail(detail) {
  if (typeof detail === 'string' && detail.trim()) return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map(item => typeof item === 'string' ? item : item?.msg)
      .filter(message => typeof message === 'string' && message.trim())

    if (messages.length > 0) return messages.join('; ')
  }

  return null
}

export function extractApiErrorMessage(payload) {
  if (!payload || typeof payload !== 'object') return null

  for (const value of [payload.error, payload.message]) {
    if (typeof value === 'string' && value.trim()) return value
  }

  return extractDetail(payload.detail)
}

export function getApiErrorMessage(error, translate) {
  const backendMessage = extractApiErrorMessage(error?.response?.data)
  if (backendMessage) return backendMessage

  if (error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT') {
    return translate('api.requestTimeout')
  }

  if (error?.message === 'Network Error' || (!error?.response && error?.request)) {
    return translate('api.networkError')
  }

  const status = error?.response?.status
  if (status) return translate('api.requestFailedStatus', { status })

  return error?.message || translate('api.requestFailed')
}
