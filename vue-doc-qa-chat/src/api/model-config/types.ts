/**
 * 模型配置类型定义
 */

/** 模型配置类型 */
export interface ModelConfigType {
  id: string
  config_type: 'chat' | 'embedding'
  model_name: string
  api_key: string
  base_url: string
  is_active: boolean
  remark: string | null
  created_at: string
  updated_at: string
}

/** 创建模型配置参数 */
export interface ModelConfigCreateType {
  config_type: 'chat' | 'embedding'
  model_name: string
  api_key: string
  base_url: string
  is_active?: boolean
  remark?: string
}

/** 更新模型配置参数 */
export interface ModelConfigUpdateType {
  config_type?: 'chat' | 'embedding'
  model_name?: string
  api_key?: string
  base_url?: string
  is_active?: boolean
  remark?: string
}
