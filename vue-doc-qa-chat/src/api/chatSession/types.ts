export interface ChatSessionRequestType {
  id?: string
  title?: string
  date?: string
}

export interface ChatSessionResponseType {
  id: string
  title: string
  date: string
  messages?: Array<{
    type: 'ai' | 'human'
    content: string
    timestamp: string
  }>
}

// 单个聊天消息的类型定义
export interface ChatMessageType {
  id: string
  role: string
  content: string
  think: string
  chat_session_id: string
  date: string
}

// 聊天历史响应的类型定义
export interface ChatHistoryResponseType {
  id: string
  title: string
  timestamp: string
  messageCount: number
  messages: ChatMessageType[]
}

// 保留其他原有接口
export interface ChatRequestType {
  model?: string
  stream?: boolean
  messages: {
    role: string
    content: string
  }
}

export interface ChatResponseType {
  code: number
  message: string
}
