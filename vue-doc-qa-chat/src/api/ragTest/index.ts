import type { CustomAxiosConfig } from '@/http/types'
import type { RagTestParamsType, ResponseRagTestPageType } from './types'
import http from '@/http'

const ragTestPageApi = (params: RagTestParamsType) => {
  return http.get<ResponseRagTestPageType>('/rag-test/page', params)
}

// 修改为支持文件上传的接口
const ragTestGenerateApi = (data: FormData, config?: CustomAxiosConfig) => {
  return http.post<string>('/rag-test/generate', data, config)
}

const ragTestDeleteApi = (id: string) => {
  return http.delete<string>('/rag-test/delete', { id: id })
}

const ragTestExportApi = (id: string) => {
  return http.download('/rag-test/export', { id: id })
}

const ragTestTaskStatusApi = (taskId: string) => {
  return http.get(`/rag-test/task/${taskId}`)
}

export { ragTestPageApi, ragTestGenerateApi, ragTestDeleteApi, ragTestExportApi, ragTestTaskStatusApi }
