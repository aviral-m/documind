export interface LivenessResponse {
  status: 'ok'
}

export interface DatabaseHealthResponse {
  status: 'ok'
  database: 'connected'
  latency_ms: number
}
