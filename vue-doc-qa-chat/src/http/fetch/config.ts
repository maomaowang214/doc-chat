import qs from 'qs'
import type { FetchConfig, FetchResponse } from '../types'
import InterceptorManager from './InterceptorManager'
import { checkStatus } from '../helper/checkStatus'
import { addPending, removePending } from '../helper/abortController'
import { ContentTypeEnum, ResultEnum } from '@/enums/httpEnum'
import HttpError from '../helper/httpError'

/** 默认baseUrl */
const PATH_URL = import.meta.env.VITE_API_BASEURL

const defaultConfig: FetchConfig = {
  method: 'GET',
  /** 基本路径 */
  baseURL: PATH_URL,
  /** 请求超时时间 */
  timeout: ResultEnum.TIMEOUT as number,
  headers: {
    'Content-Type': ContentTypeEnum.JSON
  }
}

/**
 * 请求拦截器
 * @returns 请求拦截器管理
 */
/**
 * 请求拦截器
 * @returns 请求拦截器管理
 */
function requestInterceptor<T>(interceptors: InterceptorManager<FetchConfig<T>>) {
  // 添加请求拦截器
  interceptors.use({
    onFulfilled: config => {
      // 取消重复的请求，需要当前url请求完成后，才会重新请求。
      config.cancel ??= true
      // 请求开始，在 AbortController 管理中添加该请求
      config.cancel && addPending(config)

      // **新增：检测流式请求并自动添加 SSE 头部**
      if (config.onStream) {
        console.log('🌊 [请求拦截] 检测到流式请求，添加SSE头部')
        config.headers = {
          ...config.headers,
          Accept: 'text/event-stream',
          'Cache-Control': 'no-cache'
        }
      }

      return config
    },
    onRejected: error => {
      return Promise.reject(new HttpError(400, error.message))
    }
  })

  return interceptors
}

/**
 * 响应拦截器
 * @returns 响应拦截器管理
 */
function responseInterceptor<T>(interceptors: InterceptorManager<FetchResponse<T>>) {
  let fetchConfig: FetchConfig
  // 添加响应拦截器，处理 Fetch 返回的数据，此时 response 还需要进一步处理
  interceptors.use({
    onFulfilled: response => {
      console.log('📥 [响应拦截器] 收到响应')
      console.log('📥 [响应拦截器] status:', response.status)
      console.log('📥 [响应拦截器] ok:', response.ok)
      console.log('📥 [响应拦截器] content-type:', response.headers.get('content-type'))

      if (!response.ok) {
        console.error('❌ [响应拦截器] 响应不成功')
        return Promise.reject(response.json())
      }
      const { config } = response
      config && (fetchConfig = config)
      console.log('🔍 [响应拦截器] config.onStream 存在:', !!config?.onStream)
      // **检查是否为流式响应**
      if (config?.onStream) {
        console.log('🌊 [响应拦截器] 检测到流式请求，调用 handleStream')
        return handleStream<T>(response, config)
      }
      // 普通响应处理...
      const contentType = response.headers.get('content-type') || ''
      console.log('📄 [响应拦截器] 普通响应处理，content-type:', contentType)

      if (contentType.includes('application/json')) {
        return response.json()
      } else if (contentType.startsWith('text/')) {
        return response.text()
      } else if (contentType.includes('image/')) {
        return response.blob()
      } else if (contentType.includes('multipart/form-data')) {
        return response.formData()
      }
      return response.text()
    },
    onRejected: error => {
      console.error('❌ [响应拦截器] 响应错误:', error)
      return Promise.reject(new HttpError(error.code || 400, error.message))
    }
  })

  /**
   * 添加响应拦截器，处理最终的数据和错误信息。
   */
  interceptors.use({
    onFulfilled: response => {
      // 请求响应完成，在 AbortController 管理中移除该请求
      removePending(fetchConfig)
      return response
    },
    onRejected: async error => {
      // 处理服务器返回 5xx 的错误信息
      const response = await error
      // 统一处理 promise 链的 reject 错误。
      return Promise.reject(checkStatus(response.code, response.message))
    }
  })

  return interceptors
}

/**
 * 处理 SSE 流式响应
 */
async function handleStream<T>(response: FetchResponse<T>, config: FetchConfig<T>) {
  console.log('🌊 [前端流处理] 开始处理')

  if (!config.onStream || !response.body) {
    throw new Error('流处理配置错误')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  config.onReady && config.onReady(response)

  let buffer = ''
  let eventCount = 0
  let isProcessing = true

  try {
    while (isProcessing) {
      console.log('🔄 [前端流处理] 等待读取chunk...')

      const { done, value } = await reader.read()

      console.log('📨 [前端流处理] 读取结果 - done:', done, 'value长度:', value?.length)

      if (done) {
        console.log('✅ [前端流处理] 流读取完成，总共处理', eventCount, '个事件')
        break
      }

      if (!value) {
        console.warn('⚠️ [前端流处理] 收到空数据块')
        continue
      }

      const chunk = decoder.decode(value, { stream: true })
      buffer += chunk

      console.log('📨 [前端流处理] 收到数据块:', chunk)

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      console.log('📝 [前端流处理] 分割得到', lines.length, '行数据')

      for (const line of lines) {
        if (line.trim() === '') continue

        console.log('📄 [前端流处理] 处理行:', line)

        try {
          // 支持 NDJSON 格式（后端返回纯 JSON 行）
          const eventData = JSON.parse(line)
          eventCount++

          console.log('📨 [前端流处理] 第', eventCount, '个事件')

          // 处理 NDJSON 格式的响应（后端 chat 接口）
          if (eventData.message && eventData.message.content !== undefined) {
            const content = eventData.message.content

            if (content) {
              console.log('📝 [前端流处理] 收到内容:', content)

              try {
                config.onStream(reader, content)
                console.log('✅ [前端流处理] onStream 回调执行成功')
              } catch (callbackError) {
                console.error('❌ [前端流处理] onStream 回调执行失败:', callbackError)
              }
            }

            // 检查是否完成
            if (eventData.done === true) {
              console.log('🏁 [前端流处理] 内容生成完成')
              isProcessing = false
              return Promise.resolve({
                code: 200,
                message: '流式响应完成',
                data: { eventCount }
              } as any)
            }
          }
          // 兼容 SSE 格式（如果有 type 字段）
          else if (eventData.type) {
            switch (eventData.type) {
              case 'connected':
                console.log('🔗 [前端流处理] 连接已建立')
                break

              case 'start':
                console.log('🚀 [前端流处理] 开始生成内容')
                break

              case 'answer':
                if (eventData.chunk) {
                  console.log('📝 [前端流处理] 收到答案chunk:', eventData.chunk)

                  try {
                    config.onStream(reader, eventData.chunk)
                    console.log('✅ [前端流处理] onStream 回调执行成功')
                  } catch (callbackError) {
                    console.error('❌ [前端流处理] onStream 回调执行失败:', callbackError)
                  }
                }
                break

              case 'end':
                console.log('🏁 [前端流处理] 内容生成完成')
                isProcessing = false
                return Promise.resolve({
                  code: 200,
                  message: '流式响应完成',
                  data: { eventCount }
                } as any)

              case 'error':
                console.error('❌ [前端流处理] 服务器错误:', eventData.message)
                throw new Error(eventData.message || '服务器处理错误')

              default:
                console.warn('⚠️ [前端流处理] 未知事件类型:', eventData.type)
            }
          }
        } catch (parseError) {
          // 尝试处理 SSE 格式 (data: {...})
          if (line.startsWith('data: ')) {
            try {
              const jsonData = line.slice(6)
              const eventData = JSON.parse(jsonData)
              eventCount++
              // SSE 格式处理（保持向后兼容）
              if (eventData.chunk) {
                config.onStream(reader, eventData.chunk)
              }
            } catch (sseParseError) {
              console.error('❌ [前端流处理] SSE解析失败:', line, sseParseError)
            }
          } else {
            console.error('❌ [前端流处理] 解析事件数据失败:', line, parseError)
          }
        }
      }
    }

    console.log('🏁 [前端流处理] 流处理完成，总共处理', eventCount, '个事件')
    return Promise.resolve({
      code: 200,
      message: '流式响应完成',
      data: { eventCount }
    } as any)
  } catch (error) {
    console.error('❌ [前端流处理] 处理失败:', error)
    throw error
  } finally {
    isProcessing = false
    console.log('🧹 [前端流处理] 释放reader资源')
    try {
      reader.releaseLock()
      console.log('✅ [前端流处理] reader资源释放成功')
    } catch (releaseError) {
      console.error('❌ [前端流处理] reader资源释放失败:', releaseError)
    }
  }
}

/**
 * Fecth 请求
 * @param url url路径，可以是完整的 url。如果不是完整的，则会从 PATH_URL 中拼接
 * @param config 请求参数配置
 * @returns 返回响应数据 Promise
 */
async function fetchRequest<T = any>(url: string, config: FetchConfig<T> = {}): Promise<T> {
  let requestInterceptors = new InterceptorManager<FetchConfig<T>>()
  let responseInterceptors = new InterceptorManager<FetchResponse<T>>()

  requestInterceptors = requestInterceptor<T>(requestInterceptors)
  responseInterceptors = responseInterceptor<T>(responseInterceptors)

  // 合并基础配置
  const mergedConfig: FetchConfig = {
    ...defaultConfig,
    ...config
  }

  // 处理URL
  let finalURL = url
  if (PATH_URL && !url.startsWith('http')) {
    finalURL = PATH_URL + url
  }
  // 处理查询参数
  if (mergedConfig.params) {
    const params = qs.stringify(mergedConfig.params)
    finalURL += `?${params.toString()}`
  }
  // 处理请求数据
  if (mergedConfig.data) {
    mergedConfig.body = JSON.stringify(mergedConfig.data)
  }
  mergedConfig.url = finalURL

  // 创建 Fetch Promise 链，流程：（请求拦截器 → Fetch请求 → 响应拦截器）
  let promise = Promise.resolve(mergedConfig)

  const requestInterceptorChain: any[] = []
  requestInterceptors.forEach(interceptor => {
    requestInterceptorChain.push(interceptor.onFulfilled, interceptor.onRejected)
  })

  const responseInterceptorChain: any[] = []
  responseInterceptors.forEach(interceptor => {
    responseInterceptorChain.push(interceptor.onFulfilled, interceptor.onRejected)
  })

  // 将请求拦截器依次添加到 promise 链
  let i = 0
  while (i < requestInterceptorChain.length) {
    promise = promise.then(requestInterceptorChain[i++], requestInterceptorChain[i++])
  }

  // Fetch 请求添加到 promise 链
  promise = promise.then(async newConfig => {
    const response = (await fetch(finalURL, newConfig)) as FetchResponse
    // 将 config 添加到 FetchResponse 中，响应拦截器需要用到 confog
    response.config = newConfig
    return response
  })

  // 响应拦截器依次添加到 promise 链
  i = 0
  while (i < responseInterceptorChain.length) {
    promise = promise.then(responseInterceptorChain[i++], responseInterceptorChain[i++])
  }

  return promise as Promise<T>
}

export { fetchRequest }
