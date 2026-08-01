import service from './index'

export const createSimulation = (data) => {
  return service.post('/api/simulation/create', data)
}

export const prepareSimulation = (data) => {
  return service.post('/api/simulation/prepare', data)
}

export const getPrepareStatus = (data) => {
  return service.post('/api/simulation/prepare/status', data)
}

export const getSimulation = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}`)
}

export const getSimulationProfiles = (simulationId, platform) => {
  const params = platform ? { platform } : {}
  return service.get(`/api/simulation/${simulationId}/profiles`, { params })
}

export const getSimulationProfilesRealtime = (simulationId, platform) => {
  const params = platform ? { platform } : {}
  return service.get(`/api/simulation/${simulationId}/profiles/realtime`, { params })
}

export const getSimulationConfig = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/config`)
}

export const getSimulationConfigRealtime = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/config/realtime`)
}

export const listSimulations = (projectId) => {
  const params = projectId ? { project_id: projectId } : {}
  return service.get('/api/simulation/list', { params })
}

export const startSimulation = (data) => {
  return service.post('/api/simulation/start', data)
}

export const stopSimulation = (data) => {
  return service.post('/api/simulation/stop', data)
}

export const getRunStatus = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/run-status`)
}

export const getRunStatusDetail = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/run-status/detail`)
}

export const getSimulationPosts = (simulationId, platform, limit = 50, offset = 0) => {
  const params = { limit, offset }
  if (platform) params.platform = platform
  return service.get(`/api/simulation/${simulationId}/posts`, { params })
}

export const getSimulationTimeline = (simulationId, startRound = 0, endRound = null) => {
  const params = { start_round: startRound }
  if (endRound !== null) {
    params.end_round = endRound
  }
  return service.get(`/api/simulation/${simulationId}/timeline`, { params })
}

export const getAgentStats = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/agent-stats`)
}

export const getSimulationActions = (simulationId, params = {}) => {
  return service.get(`/api/simulation/${simulationId}/actions`, { params })
}

export const closeSimulationEnv = (data) => {
  return service.post('/api/simulation/close-env', data)
}

export const getEnvStatus = (data) => {
  return service.post('/api/simulation/env-status', data)
}

export const interviewAgents = (data) => {
  return service.post('/api/simulation/interview/batch', data)
}

export const getSimulationHistory = (limit = 20) => {
  return service.get('/api/simulation/history', { params: { limit } })
}
