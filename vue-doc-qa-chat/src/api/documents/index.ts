import type { CustomAxiosConfig } from '@/http/types'
import type { DocParamsType, ResponseDocPageType, VectorProgressType } from './types'
import http from '@/http'

const docPageApi = (params: DocParamsType) => {
  return http.get<ResponseDocPageType>('/documents/page', params)
}

const docAddApi = (data: FormData, config?: CustomAxiosConfig) => {
  return http.post<string>('/documents/add', data, config)
}

const docEditApi = (data: FormData, config?: CustomAxiosConfig) => {
  return http.put<string>('/documents/update', data, config)
}

const docDeleteApi = (id: string) => {
  return http.delete<string>('/documents/delete', { id: id })
}

const docDownloadApi = (id: string) => {
  // 使用正确的后端路径 /documents/read/{item_id}
  return http.get<Blob>(`/documents/read/${id}`, undefined, { responseType: 'blob' })
}

/**
 * 文档全部向量化 Api（同步，阻塞式）
 * @param config axios config配置
 */
const docVectorAllApi = (config?: CustomAxiosConfig) => {
  return http.get<string>('/documents/vector-all', undefined, config)
}

/**
 * 获取向量化进度
 */
const docVectorProgressApi = () => {
  return http.get<VectorProgressType>('/documents/vector-progress')
}

/**
 * 创建向量化 SSE 连接（流式获取进度）
 * @param onProgress 进度回调函数
 * @param onComplete 完成回调函数
 * @param onError 错误回调函数
 */
const createVectorStreamConnection = (
  onProgress: (data: VectorProgressType) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): EventSource => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
  const eventSource = new EventSource(`${baseUrl}/documents/vector-all-stream`)

  eventSource.onmessage = (event) => {
    try {
      const data: VectorProgressType = JSON.parse(event.data)
      onProgress(data)

      if (data.status === 'completed' || data.status === 'error' || data.status === 'timeout') {
        eventSource.close()
        onComplete()
      }
    } catch (e) {
      console.error('解析 SSE 数据失败:', e)
    }
  }

  eventSource.onerror = (error) => {
    console.error('SSE 连接错误:', error)
    eventSource.close()
    onError(new Error('向量化连接中断'))
  }

  return eventSource
}

export {
  docPageApi,
  docAddApi,
  docEditApi,
  docDeleteApi,
  docDownloadApi,
  docVectorAllApi,
  docVectorProgressApi,
  createVectorStreamConnection
}
