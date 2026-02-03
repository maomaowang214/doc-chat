interface RagTestParamsType {
  page_num: number
  page_size: number
  id?: string
  name?: string
  doc_id?: string
  status?: string
}

interface RagTestType {
  id: string
  name: string
  doc_id: string
  doc_name: string
  questions: number
  status: string
  date: string
}

interface ResponseRagTestPageType {
  pageNum: number
  pageSize: number
  total: number
  list: RagTestType[]
}

interface TaskStatus {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string
  resultFile?: string
  createdAt: string
  completedAt?: string
  error?: string
}

export type { RagTestParamsType, RagTestType, ResponseRagTestPageType, TaskStatus }
