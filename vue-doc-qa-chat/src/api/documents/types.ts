interface DocParamsType {
  page_num: number
  page_size: number
  id?: string
  name?: string
}

interface ResponseDocPageType {
  page_num: number
  page_size: number
  total: number
  list: DocTableType[]
}

interface DocTableType {
  id: string
  name: string
  file_name: string
  file_path: string
  suffix: string
  vector: string
  date: string
}

/**
 * 向量化进度类型
 */
interface VectorProgressType {
  /** 状态: idle, loading, splitting, vectorizing, completed, error, timeout */
  status: 'idle' | 'loading' | 'splitting' | 'vectorizing' | 'completed' | 'error' | 'timeout'
  /** 当前处理的文档数 */
  current: number
  /** 总文档数 */
  total: number
  /** 状态消息 */
  message: string
  /** 错误信息 */
  error: string | null
  /** 已用时间（秒） */
  elapsed: number
  /** 当前批次 */
  batch_current: number
  /** 总批次数 */
  batch_total: number
  /** 进度百分比 */
  progress: number
}

export type { DocParamsType, ResponseDocPageType, DocTableType, VectorProgressType }
