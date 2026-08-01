import test from 'node:test'
import assert from 'node:assert/strict'

import { extractApiErrorMessage, getApiErrorMessage } from '../src/api/errors.js'

const translate = (key, params = {}) => `${key}:${params.status || ''}`

test('extractApiErrorMessage preserves actionable backend errors', () => {
  assert.equal(extractApiErrorMessage({ error: 'Project not found' }), 'Project not found')
  assert.equal(extractApiErrorMessage({ message: 'Invalid request' }), 'Invalid request')
})

test('extractApiErrorMessage flattens validation details', () => {
  const payload = { detail: [{ msg: 'Project ID is required' }, { msg: 'File is invalid' }] }
  assert.equal(extractApiErrorMessage(payload), 'Project ID is required; File is invalid')
})

test('getApiErrorMessage localizes transport failures', () => {
  assert.equal(getApiErrorMessage({ code: 'ECONNABORTED' }, translate), 'api.requestTimeout:')
  assert.equal(getApiErrorMessage({ message: 'Network Error', request: {} }, translate), 'api.networkError:')
  assert.equal(
    getApiErrorMessage({ response: { status: 503, data: {} } }, translate),
    'api.requestFailedStatus:503'
  )
})

test('getApiErrorMessage gives backend messages priority', () => {
  const error = {
    message: 'Request failed with status code 400',
    response: { status: 400, data: { error: 'Simulation ID is required' } }
  }

  assert.equal(getApiErrorMessage(error, translate), 'Simulation ID is required')
})
