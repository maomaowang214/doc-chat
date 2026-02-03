import type {
  ModelConfigType,
  ModelConfigCreateType,
  ModelConfigUpdateType
} from './types'
import http from '@/http'

/**
 * 获取所有模型配置
 */
const modelConfigListApi = () => {
  return http.get<ModelConfigType[]>('/model-config/list')
}

/**
 * 根据类型获取模型配置
 * @param configType chat 或 embedding
 */
const modelConfigListByTypeApi = (configType: string) => {
  return http.get<ModelConfigType[]>(`/model-config/list/${configType}`)
}

/**
 * 添加模型配置
 */
const modelConfigAddApi = (data: ModelConfigCreateType) => {
  return http.post<ModelConfigType>('/model-config/add', data)
}

/**
 * 更新模型配置
 */
const modelConfigUpdateApi = (id: string, data: ModelConfigUpdateType) => {
  return http.put<ModelConfigType>(`/model-config/update/${id}`, data)
}

/**
 * 删除模型配置
 */
const modelConfigDeleteApi = (id: string) => {
  return http.delete<any>(`/model-config/delete/${id}`)
}

/**
 * 设置为启用
 */
const modelConfigSetActiveApi = (id: string) => {
  return http.put<ModelConfigType>(`/model-config/set-active/${id}`)
}

/**
 * 初始化默认配置
 */
const modelConfigInitDefaultApi = () => {
  return http.post<any>('/model-config/init-default')
}

export {
  modelConfigListApi,
  modelConfigListByTypeApi,
  modelConfigAddApi,
  modelConfigUpdateApi,
  modelConfigDeleteApi,
  modelConfigSetActiveApi,
  modelConfigInitDefaultApi
}
