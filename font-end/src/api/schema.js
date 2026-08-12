import service from '@/api/axios'

// 生成schema
export function getSchema(params) {
  return service.get('/api/schemas/generate', { params })
}