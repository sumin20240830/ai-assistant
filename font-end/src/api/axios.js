import axios from 'axios'

const service = axios.create({
  baseURL: 'http://127.0.0.1:8000', // 对应FastAPI服务地址
  timeout: 90000 // LLM 生成和自动修复可能需要较长时间
})

export default service
