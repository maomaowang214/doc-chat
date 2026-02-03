<script setup lang="ts">
import type { Ref } from 'vue'
import type { ChatSessionResponseType } from '@/api/chatSession/types'
import { nextTick, onMounted, onUnmounted, ref, computed } from 'vue'
import { chatApi, chatCancelRequest, chatHistoryApi } from '@/api/chat'
import { chatSessionsAddApi } from '@/api/chatSession'
import { docPageApi } from '@/api/documents'

import { FolderOpened, Loading, Document, ArrowUp, InfoFilled, WarningFilled, Refresh } from '@element-plus/icons-vue'
import HumanChat from './components/HumanChat.vue'
import AssistantChat from './components/AssistantChat.vue'
import ChatHistory from './components/ChatHistory.vue'

/** 配置组件名，使 KeepAlive 能找到该组件 */
defineOptions({ name: 'Chat' })

type Chat = {
  type: string
  content: string
  think?: string
  isStream?: boolean
  error?: boolean | string
}

/** 对话id */
const chatSessionId = ref('')
const chatTitle = ref('')

/** 知识库相关 */
const knowledgeEnabled = ref(true) // 是否启用知识库
const knowledgeLoading = ref(false)
const knowledgeList = ref<Array<{ id: string; name: string; vector: string }>>([])

/** 获取知识库列表（已向量化的文档） */
const getKnowledgeList = async () => {
  knowledgeLoading.value = true
  try {
    const res = await docPageApi({ page_num: 1, page_size: 100 })
    // 只显示已向量化的文档
    knowledgeList.value = res.data.list
      .filter((item: any) => item.vector === 'yes')
      .map((item: any) => ({
        id: item.id,
        name: item.name,
        vector: item.vector
      }))
  } catch (error) {
    console.error('获取知识库列表失败:', error)
  } finally {
    knowledgeLoading.value = false
  }
}

/** 计算知识库状态文本 */
const knowledgeStatusText = computed(() => {
  if (!knowledgeEnabled.value) {
    return '未启用知识库'
  }
  if (knowledgeList.value.length === 0) {
    return '暂无可用知识库'
  }
  return `已启用 ${knowledgeList.value.length} 个知识库`
})

/** 响应式对话，界面显示历史 */
const chatting: Ref<Chat[]> = ref([])
/** 用户输入消息 */
const humanInput = ref('')

const loading = ref(false)
const disabled = ref(false)
/** 历史会话列表框显隐 */
const historyVisible = ref(false)

/** 监听 assistant 是否正在流式输出文字 */
const isStream = ref(false)
/** 监听是否使用了鼠标滚轮 */
const isWheelMove = ref(false)

const chatMainRef = ref<HTMLDivElement>()

/**
 * 历史记录列表，item点击事件
 * 后端 /chat/history 返回的 data 为消息数组，需映射为前端 Chat 格式
 * @param chatSession 会话记录
 */
const onHistoryItemClick = async (chatSession: ChatSessionResponseType) => {
  const response = await chatHistoryApi(chatSession.id)
  const list = Array.isArray(response.data) ? response.data : []
  chatting.value = list.map((item: { role: string; content: string; think?: string }) => ({
    type: item.role === 'user' ? 'human' : 'ai',
    content: item.content || '',
    think: item.think || '',
    isStream: false,
    error: false
  }))
  chatTitle.value = chatSession.title
  chatSessionId.value = chatSession.id
  scrollToButtom(chatMainRef.value!)
}

/**
 * 会话重命名标题后的回调
 */
const onHistoryItemRename = (title: string, id: string) => {
  // 如果重命名的会话记录和当前正在聊天的会话相同，则更新标题
  if (chatSessionId.value === id) {
    chatTitle.value = title
  }
}

const onHistoryItemDelete = (id: string) => {
  if (chatSessionId.value === id) {
    onRestartNewChat()
  }
}

/**
 * 输入框提交
 */
const onSubmit = async () => {
  if (humanInput.value === '') {
    ElMessage.warning('请输入对话内容。')
    return
  }
  if (!chatSessionId.value) {
    disabled.value = true
    loading.value = true

    try {
      const res = await chatSessionsAddApi({ title: humanInput.value })
      chatSessionId.value = res.data.id
      chatTitle.value = res.data.title
      startChatting()
    } catch {
      disabled.value = false
      loading.value = false
    }
  } else {
    startChatting()
  }
}

/**
 * 开始对话，流式响应
 */
function startChatting() {
  console.log('chatSessionId.value-开始对话', chatSessionId.value)
  disabled.value = true
  loading.value = true
  isWheelMove.value = false
  scrollToButtom(chatMainRef.value!)

  const userChat = ref<Chat>({
    type: 'human',
    content: humanInput.value,
    error: false
  })
  const assistantChat = ref<Chat>({
    type: 'ai',
    content: '',
    think: '',
    isStream: false,
    error: false
  })

  // 请求参数
  const data = {
    messages: {
      role: userChat.value.type === 'human' ? 'user' : 'assistant',
      content: userChat.value.content
    },
    chat_session_id: chatSessionId.value,
    stream: true,
    use_knowledge: knowledgeEnabled.value && knowledgeList.value.length > 0
  }

  let isThinking = false
  let buffer = ''

  // 请求后台 chat
  chatApi(
    data,
    () => {
      // onReady 回调
      humanInput.value = ''
      chatting.value.push(userChat.value)
      chatting.value.push(assistantChat.value)
      assistantChat.value.isStream = true
      isStream.value = true
      loading.value = false
    },
    (_reader, chunk) => {
      // onStream 回调 - 这里 chunk 就是服务端发送的内容
      console.log('🎯 [onStream回调] 收到chunk:', chunk)

      try {
        // chunk 直接就是内容，不需要额外解析
        const content = chunk as string

        // 处理思考标签
        if (content === '<think>') {
          isThinking = true
          return
        }
        if (content === '</think>') {
          isThinking = false
          return
        }

        // 根据是否在思考状态分别处理
        if (isThinking) {
          assistantChat.value.think += content
        } else {
          assistantChat.value.content += content
        }

        // 滚动处理
        if (content.indexOf('\n') !== -1) {
          buffer = ''
          scrollToButtom(chatMainRef.value!)
        }
        buffer += content

        if (!isWheelMove.value && buffer.length >= 50) {
          scrollToButtom(chatMainRef.value!)
        }

        if (buffer.length >= 50) {
          buffer = ''
        }

        console.log('✅ [onStream回调] 处理完成')
      } catch (error) {
        console.error('❌ [onStream回调] 处理失败:', error)
      }
    }
  )
    .catch(error => {
      console.error('❌ [聊天请求] 失败:', error)
      userChat.value.error = error.message
      assistantChat.value.error = error.message
    })
    .finally(() => {
      console.log('🏁 [聊天请求] 完成')
      disabled.value = false
      loading.value = false
      isStream.value = false
      assistantChat.value.isStream = false
    })
}

/**
 * 输入框键盘事件
 * @param event KeyboardEvent
 */
const inputKeyboard = (event: KeyboardEvent | Event) => {
  const e = event as KeyboardEvent
  // Shift + Enter 换行
  if (e.key == 'Enter' && e.shiftKey) {
    return
  }
  // Ctrl + Enter 换行
  if (e.key == 'Enter' && e.ctrlKey) {
    humanInput.value = humanInput.value + '\n'
  } else if (e.key == 'Enter') {
    // Enter 提交
    event.preventDefault()
    onSubmit()
  }
}

/**
 * 取消请求
 */
const onCancelRequest = () => {
  chatCancelRequest()
}

/**
 * 开启新对话
 */
const onRestartNewChat = () => {
  chatSessionId.value = ''
  chatTitle.value = ''
  humanInput.value = ''
  loading.value = false
  disabled.value = false
  chatting.value = []
  chatCancelRequest()
  ElMessage.success('开始新对话。')
}

/**
 * 判断容器是否滚动到底部
 * @param element 指定目标容器 Element
 * @param threshold 误差高度阈值
 */
const isMoveToBottom = (element: HTMLDivElement | undefined, threshold: number = 1): boolean => {
  if (!element) {
    return false
  }
  const { scrollTop, clientHeight, scrollHeight } = element
  return scrollTop + clientHeight >= scrollHeight - threshold
}

/**
 * 鼠标滚轮监听事件
 */
const handleWhell = () => {
  isWheelMove.value = true
}

/**
 * 滚动条监听事件
 */
const handleScroll = () => {
  if (isMoveToBottom(chatMainRef.value)) {
    isWheelMove.value = false
  }
}

onMounted(() => {
  document.addEventListener('wheel', handleWhell)
  document.addEventListener('scroll', handleScroll, true)
  // 获取知识库列表
  getKnowledgeList()
})

onUnmounted(() => {
  document.removeEventListener('wheel', handleWhell)
  document.removeEventListener('scroll', handleScroll)
})

function scrollToButtom(div: Element | null) {
  if (div === null) {
    return
  }

  nextTick(() => {
    div.scrollTop = div.scrollHeight
  })
}
</script>

<template>
  <div class="chat-container">
    <div class="chat-header">
      <el-tooltip class="box-item" :content="chatTitle" placement="bottom">
        <span class="title">{{ chatTitle }}</span>
      </el-tooltip>
    </div>

    <div ref="chatMainRef" class="chat-main">
      <div class="chat-content">
        <div class="chat">
          <AssistantChat key="system" :content="'您好！我是贴心的小助手，有什么可以帮助您的吗？'"></AssistantChat>
          <template v-for="(item, index) in chatting">
            <HumanChat :key="index" v-if="item.type === 'human'" :content="item.content" :error="item.error"></HumanChat>
            <AssistantChat
              :key="index"
              v-if="item.type === 'ai'"
              :content="item.content"
              :think="item.think"
              :is-stream="item.isStream"
              :hasThinkCard="true"
              :error="item.error"
            ></AssistantChat>
          </template>
        </div>

        <div class="chat-input-container">
          <div class="chat-loading" v-if="loading">
            <ChatLoading></ChatLoading>
          </div>
          <div class="input-card">
            <el-input
              v-model="humanInput"
              class="chat-send-input"
              type="textarea"
              :autofocus="true"
              :autosize="{ minRows: 3, maxRows: 20 }"
              :readonly="disabled"
              maxlength="2000"
              show-word-limit
              @keydown.enter="inputKeyboard"
              placeholder="请输入对话内容……"
            >
            </el-input>

            <div class="bottom-send">
              <el-button v-if="isStream" type="primary" round @click="onCancelRequest">
                <StopIcon size="20px" />
              </el-button>
              <el-button v-else type="primary" round :loading="loading" :disabled="disabled" @click="onSubmit">
                <SendIcon size="20px" />
              </el-button>
            </div>

            <div class="chat-send-bottom-controls">
              <div class="knowledge-status">
                <el-popover
                  placement="top-start"
                  :width="320"
                  trigger="click"
                  :show-arrow="true"
                  popper-class="knowledge-popover-container"
                >
                  <template #reference>
                    <div class="knowledge-trigger" :class="{ active: knowledgeEnabled && knowledgeList.length > 0 }">
                      <el-icon class="knowledge-icon"><FolderOpened /></el-icon>
                      <span class="knowledge-text">{{ knowledgeStatusText }}</span>
                      <el-icon class="arrow-icon"><ArrowUp /></el-icon>
                    </div>
                  </template>
                  <div class="knowledge-popover">
                    <div class="knowledge-header">
                      <div class="header-left">
                        <el-icon class="header-icon"><FolderOpened /></el-icon>
                        <span class="header-title">知识库</span>
                      </div>
                      <el-switch
                        v-model="knowledgeEnabled"
                        size="small"
                        :active-text="knowledgeEnabled ? '已启用' : ''"
                        inline-prompt
                      />
                    </div>

                    <div class="knowledge-body">
                      <div v-if="!knowledgeEnabled" class="knowledge-disabled">
                        <el-icon class="disabled-icon"><InfoFilled /></el-icon>
                        <span>关闭知识库后，AI 将使用通用知识回答</span>
                      </div>

                      <template v-else>
                        <div v-if="knowledgeLoading" class="knowledge-loading">
                          <el-icon class="is-loading"><Loading /></el-icon>
                          <span>加载知识库...</span>
                        </div>

                        <div v-else-if="knowledgeList.length === 0" class="knowledge-empty">
                          <el-icon class="empty-icon"><WarningFilled /></el-icon>
                          <span>暂无可用知识库</span>
                          <el-text type="info" size="small">请先上传文档并构建知识库</el-text>
                        </div>

                        <div v-else class="knowledge-content">
                          <div class="knowledge-tip">
                            <el-icon><InfoFilled /></el-icon>
                            <span>AI 将基于以下 {{ knowledgeList.length }} 个文档回答问题</span>
                          </div>
                          <div class="knowledge-list">
                            <div v-for="item in knowledgeList" :key="item.id" class="knowledge-item">
                              <el-icon class="item-icon"><Document /></el-icon>
                              <span class="item-name">{{ item.name }}</span>
                              <el-tag size="small" type="success" effect="plain">已构建</el-tag>
                            </div>
                          </div>
                        </div>
                      </template>
                    </div>

                    <div class="knowledge-footer">
                      <el-button size="small" text @click="getKnowledgeList">
                        <el-icon><Refresh /></el-icon>
                        刷新列表
                      </el-button>
                    </div>
                  </div>
                </el-popover>
              </div>
              <el-text type="info" size="small">内容由 AI 生成，请仔细甄别</el-text>
              <div class="send-controls-extra">
                <el-button-group>
                  <el-popover
                    :popper-style="{ borderRadius: '26px' }"
                    :visible="historyVisible"
                    placement="top-end"
                    :width="350"
                    trigger="click"
                    :persistent="false"
                  >
                    <template #reference>
                      <el-button round @click="historyVisible = !historyVisible">历史对话</el-button>
                    </template>
                    <ChatHistory
                      v-model:visible="historyVisible"
                      v-model:active-id="chatSessionId"
                      @item-click="onHistoryItemClick"
                      @rename="onHistoryItemRename"
                      @delete="onHistoryItemDelete"
                    />
                  </el-popover>

                  <el-button round type="primary" @click="onRestartNewChat">新对话</el-button>
                </el-button-group>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.chat-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: #343541;

  .chat-header {
    display: flex;
    flex: none;
    align-items: center;
    justify-content: center;
    height: 60px;
    background-color: #202123;
    border-bottom: 1px solid #444654;

    .title {
      max-width: 1000px;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: 18px;
      font-weight: bold;
      white-space: nowrap;
      color: #e5e5e5;
    }
  }

  .chat-main {
    position: relative;
    display: flex;
    flex: 1;
    justify-content: center;
    width: 100%;
    min-height: calc(100% - 60px);
    overflow: auto;

    .chat-content {
      position: relative;
      display: flex;
      flex-grow: 1;
      flex-direction: column;
      max-width: 1000px;
      height: 100%;

      .chat {
        box-sizing: border-box;
        flex: 1;
        width: 100%;
        padding: 0 20px 30px;
      }

      .chat-input-container {
        position: sticky;
        bottom: 0;
        z-index: 1;
        box-sizing: border-box;
        display: flex;
        flex-shrink: 0;
        flex-direction: column;
        align-items: center;
        width: 100%;
        margin-top: auto;

        .chat-loading {
          margin-bottom: 5px;
        }

        .input-card {
          position: relative;
          box-sizing: border-box;
          width: 100%;
          padding: 20px;
          background-color: #444654;
          border-radius: 26px 26px 0 0;
          box-shadow: rgb(0 0 0 / 18%) 4px 14px 24px 14px;

          .chat-send-input {
            flex: 1;
            /* stylelint-disable-next-line selector-class-pattern */
            :deep(.el-textarea__inner) {
              padding: 10px 66px 20px 24px;
              resize: none;
              border: 1px solid #565869;
              border-radius: 26px;
              box-shadow: none;
              color: #e5e5e5;
              background-color: #303030;

              &:focus {
                outline: none;
                box-shadow: 0 0 0 1px var(--el-color-primary-light-5) inset;
              }

              &:read-only {
                box-shadow: none;
              }
            }
            /* stylelint-disable-next-line selector-class-pattern */
            :deep(.el-input__count) {
              right: 16px;
              background-color: #303030;
            }
          }

          .bottom-send {
            position: absolute;
            right: 32px;
            bottom: 88px;
            display: flex;
            align-items: center;
            font-size: var(--el-font-size-small);

            .el-button {
              margin-left: 10px;
            }
          }

          .chat-send-bottom-controls {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 35px;
            margin-top: 10px;

            .knowledge-status {
              position: absolute;
              top: 0;
              right: 0;

              .knowledge-trigger {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.2s ease;
                font-size: 12px;
                color: #9ca3af;

                &:hover {
                  background: rgba(255, 255, 255, 0.12);
                  border-color: rgba(255, 255, 255, 0.25);
                }

                &.active {
                  background: rgba(16, 163, 127, 0.15);
                  border-color: rgba(16, 163, 127, 0.4);
                  color: #10a37f;

                  .knowledge-icon {
                    color: #10a37f;
                  }
                }

                .knowledge-icon {
                  font-size: 14px;
                  color: #9ca3af;
                }

                .knowledge-text {
                  max-width: 150px;
                  overflow: hidden;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                }

                .arrow-icon {
                  font-size: 12px;
                  transition: transform 0.2s;
                }
              }
            }

            .send-controls-extra {
              position: absolute;
              top: 0;
              left: 0;
            }
          }
        }
      }
    }
  }
}

/* 知识库弹窗样式 */
.knowledge-popover {
  padding: 0 !important;

  .knowledge-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    background: linear-gradient(135deg, rgba(16, 163, 127, 0.1) 0%, rgba(16, 163, 127, 0.05) 100%);
    border-bottom: 1px solid var(--el-border-color-lighter);

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .header-icon {
        font-size: 18px;
        color: #10a37f;
      }

      .header-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }
    }
  }

  .knowledge-body {
    padding: 16px;
    min-height: 80px;

    .knowledge-loading {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 20px 0;
      color: var(--el-text-color-secondary);
      font-size: 13px;
    }

    .knowledge-empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 20px 0;
      color: var(--el-text-color-secondary);

      .empty-icon {
        font-size: 32px;
        color: var(--el-color-warning);
      }

      span {
        font-size: 14px;
        font-weight: 500;
      }
    }

    .knowledge-disabled {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 16px;
      background: var(--el-fill-color-light);
      border-radius: 8px;
      color: var(--el-text-color-secondary);
      font-size: 13px;

      .disabled-icon {
        font-size: 16px;
        color: var(--el-color-info);
      }
    }

    .knowledge-content {
      .knowledge-tip {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 10px 12px;
        margin-bottom: 12px;
        background: rgba(16, 163, 127, 0.08);
        border-radius: 8px;
        font-size: 12px;
        color: #10a37f;

        .el-icon {
          font-size: 14px;
        }
      }

      .knowledge-list {
        max-height: 180px;
        overflow-y: auto;

        &::-webkit-scrollbar {
          width: 4px;
        }

        &::-webkit-scrollbar-thumb {
          background: var(--el-border-color);
          border-radius: 4px;
        }

        .knowledge-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 12px;
          margin-bottom: 8px;
          background: var(--el-fill-color-light);
          border-radius: 8px;
          transition: all 0.2s;

          &:last-child {
            margin-bottom: 0;
          }

          &:hover {
            background: var(--el-fill-color);
          }

          .item-icon {
            font-size: 18px;
            color: var(--el-color-primary);
            flex-shrink: 0;
          }

          .item-name {
            flex: 1;
            font-size: 13px;
            color: var(--el-text-color-primary);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .el-tag {
            flex-shrink: 0;
          }
        }
      }
    }
  }

  .knowledge-footer {
    display: flex;
    justify-content: flex-end;
    padding: 10px 16px;
    border-top: 1px solid var(--el-border-color-lighter);
    background: var(--el-fill-color-lighter);

    .el-button {
      font-size: 12px;
      color: var(--el-text-color-secondary);

      &:hover {
        color: var(--el-color-primary);
      }

      .el-icon {
        margin-right: 4px;
      }
    }
  }
}
</style>
