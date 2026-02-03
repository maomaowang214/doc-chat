<script setup lang="ts">
import { chatSessionsApi, chatSessionsDeleteApi, chatSessionsEditApi } from '@/api/chatSession'
import type { ChatSessionResponseType } from '@/api/chatSession/types'
import { onMounted, ref, toRaw, computed } from 'vue'
import { ChatLineSquare, Refresh, Close, MoreFilled, EditPen, Delete } from '@element-plus/icons-vue'

/** v-model */
const visible = defineModel('visible')
const activeId = defineModel('activeId')

/** emit */
const emit = defineEmits<{
  /** 列表Item点击事件 */
  itemClick: [chatSession: ChatSessionResponseType]
  /** 重命名提交成功触发事件 */
  rename: [title: string, chatSessionId: string]
  /** 会话删除成功触发事件 */
  delete: [chatSessionId: string]
}>()

const loading = ref(false)
const chatSessionsMap = ref(new Map<string, ChatSessionResponseType[]>())

onMounted(async () => {
  loadData()
})

/**
 * 列表项点击事件
 */
const onItemClick = async (item: ChatSessionResponseType) => {
  emit('itemClick', toRaw(item))
  visible.value = false
  activeId.value = item.id
}

/**
 * 加载会话列表
 */
async function loadData() {
  loading.value = true
  const res = await chatSessionsApi().finally(() => (loading.value = false))
  chatSessionByDate(res.data)
}

/** 计算总对话数 */
const totalCount = computed(() => {
  let count = 0
  chatSessionsMap.value.forEach(list => {
    count += list.length
  })
  return count
})

/**
 * 根据日期分组
 * @param chatSessionList 会话列表
 */
function chatSessionByDate(chatSessionList: ChatSessionResponseType[]) {
  const toData = new Date(new Date().toLocaleDateString()).getTime()
  const todayStart = toData
  const todayEnd = todayStart + 24 * 60 * 60 * 1000 - 1
  const yesterdayStart = toData - 3600 * 24 * 1000
  const yesterdayEnd = yesterdayStart + 24 * 60 * 60 * 1000 - 1
  const past7daysStart = toData - 7 * 3600 * 24 * 1000

  chatSessionsMap.value.clear()
  const todayList = []
  const yesterdayList = []
  const past7daysList = []
  const otherList = []

  for (const chatSession of chatSessionList) {
    // 获取对话记录时间戳
    const sessionDate = Date.parse(new Date(chatSession.date).toString())
    if (sessionDate >= todayStart && sessionDate <= todayEnd) {
      todayList.push(chatSession)
      chatSessionsMap.value.set('今天', todayList)
    } else if (sessionDate >= yesterdayStart && sessionDate <= yesterdayEnd) {
      yesterdayList.push(chatSession)
      chatSessionsMap.value.set('昨天', yesterdayList)
    } else if (sessionDate >= past7daysStart && sessionDate <= yesterdayStart) {
      past7daysList.push(chatSession)
      chatSessionsMap.value.set('7天内', past7daysList)
    } else {
      otherList.push(chatSession)
      chatSessionsMap.value.set('7天外', otherList)
    }
  }
}

/**
 * 列表更多按钮，下拉菜单按钮
 * @param command 下拉项回调值
 */
const onCommand = (command: { index: number; chatSession: ChatSessionResponseType }) => {
  const { index, chatSession } = command

  if (index === 1) {
    ElMessageBox.prompt('', '重命名', {
      inputValue: chatSession.title,
      inputPlaceholder: '请输入标题……',
      inputPattern: /^.+$/,
      inputErrorMessage: '文本不能为空！',
      beforeClose: async (action, instance, done) => {
        if (action === 'confirm') {
          instance.confirmButtonLoading = true
          instance.confirmButtonText = '提交中'
          const inputValue = instance.inputValue
          chatSession.title = inputValue

          const response = await chatSessionsEditApi(chatSession).finally(() => (instance.confirmButtonLoading = false))
          emit('rename', response.data.title, response.data.id)
          ElMessage.success('修改成功！')
          loadData()
          done()
        } else {
          done()
        }
      }
    }).catch(() => {})
  } else if (index === 2) {
    ElMessageBox.confirm('删除后，该对话将不可恢复。确认删除吗？', '永久删除对话', {
      type: 'error',
      beforeClose: async (action, instance, done) => {
        if (action === 'confirm') {
          instance.confirmButtonLoading = true
          instance.confirmButtonText = '提交中'

          await chatSessionsDeleteApi(chatSession.id).finally(() => (instance.confirmButtonLoading = false))
          emit('delete', chatSession.id)
          ElMessage.success('删除成功！')
          loadData()
          done()
        } else {
          done()
        }
      }
    }).catch(() => {})
  }
}
</script>

<template>
  <div class="history">
    <!-- 头部 -->
    <div class="history-header">
      <div class="header-left">
        <el-icon class="header-icon"><ChatLineSquare /></el-icon>
        <span class="header-title">历史对话</span>
        <el-tag v-if="totalCount > 0" size="small" type="info" effect="plain">{{ totalCount }}</el-tag>
      </div>
      <div class="header-right">
        <el-button size="small" :icon="Refresh" circle @click="loadData" :loading="loading" />
        <el-button size="small" :icon="Close" circle @click="visible = false" />
      </div>
    </div>

    <!-- 内容区 -->
    <div class="history-body">
      <el-skeleton :loading="loading" :rows="8" :throttle="300" animated>
        <div v-if="!loading && chatSessionsMap.size === 0" class="history-empty">
          <el-icon class="empty-icon"><ChatLineSquare /></el-icon>
          <span class="empty-text">暂无历史对话</span>
          <el-text type="info" size="small">开始新对话后，历史记录将显示在这里</el-text>
        </div>

        <ElScrollbar v-else class="history-scrollbar">
          <div class="history-content">
            <template v-for="[key, sessionList] of chatSessionsMap" :key="key">
              <div class="history-group">
                <div class="group-label">
                  <span class="label-text">{{ key }}</span>
                  <span class="label-count">{{ sessionList.length }} 条</span>
                </div>

                <div class="group-list">
                  <template v-for="item in sessionList" :key="item.id">
                    <div class="history-item" :class="{ active: activeId === item.id }">
                      <div class="item-main" @click="onItemClick(item)">
                        <el-icon class="item-icon"><ChatLineSquare /></el-icon>
                        <el-tooltip
                          :disabled="!item.title || item.title.length < 18"
                          :content="item.title"
                          placement="top-start"
                        >
                          <span class="item-title">{{ item.title }}</span>
                        </el-tooltip>
                      </div>

                      <div class="item-actions" @click.stop>
                        <el-dropdown
                          placement="bottom-end"
                          trigger="click"
                          @command="onCommand"
                        >
                          <el-button class="item-more" size="small" text circle>
                            <el-icon><MoreFilled /></el-icon>
                          </el-button>

                          <template #dropdown>
                            <el-dropdown-menu>
                              <el-dropdown-item :command="{ index: 1, chatSession: item }">
                                <el-icon><EditPen /></el-icon>
                                <span>重命名</span>
                              </el-dropdown-item>
                              <el-dropdown-item :command="{ index: 2, chatSession: item }" divided>
                                <el-icon color="#f56c6c"><Delete /></el-icon>
                                <span style="color: #f56c6c;">删除</span>
                              </el-dropdown-item>
                            </el-dropdown-menu>
                          </template>
                        </el-dropdown>
                      </div>
                    </div>
                  </template>
                </div>
              </div>
            </template>
          </div>
        </ElScrollbar>
      </el-skeleton>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.history {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 480px;

  .history-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.08) 0%, rgba(64, 158, 255, 0.02) 100%);

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .header-icon {
        font-size: 18px;
        color: var(--el-color-primary);
      }

      .header-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }

      .el-tag {
        margin-left: 4px;
      }
    }

    .header-right {
      display: flex;
      gap: 4px;

      .el-button {
        &:hover {
          color: var(--el-color-primary);
        }
      }
    }
  }

  .history-body {
    flex: 1;
    overflow: hidden;

    .history-empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      padding: 40px 20px;

      .empty-icon {
        font-size: 48px;
        color: var(--el-text-color-placeholder);
        margin-bottom: 16px;
      }

      .empty-text {
        font-size: 14px;
        font-weight: 500;
        color: var(--el-text-color-secondary);
        margin-bottom: 8px;
      }
    }

    .history-scrollbar {
      height: 100%;
    }

    .history-content {
      padding: 12px 16px;

      .history-group {
        margin-bottom: 16px;

        &:last-child {
          margin-bottom: 0;
        }

        .group-label {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 0;
          margin-bottom: 8px;
          border-bottom: 1px dashed var(--el-border-color-lighter);

          .label-text {
            font-size: 12px;
            font-weight: 600;
            color: var(--el-text-color-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }

          .label-count {
            font-size: 11px;
            color: var(--el-text-color-placeholder);
          }
        }

        .group-list {
          .history-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            margin-bottom: 6px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: var(--el-fill-color-lighter);

            &:last-child {
              margin-bottom: 0;
            }

            &:hover {
              background: var(--el-fill-color);

              .item-actions .item-more {
                opacity: 1;
              }
            }

            &.active {
              background: linear-gradient(135deg, rgba(64, 158, 255, 0.15) 0%, rgba(64, 158, 255, 0.08) 100%);
              border: 1px solid rgba(64, 158, 255, 0.3);

              .item-main {
                .item-icon {
                  color: var(--el-color-primary);
                }

                .item-title {
                  color: var(--el-color-primary);
                  font-weight: 500;
                }
              }

              .item-actions .item-more {
                opacity: 1;
              }
            }

            .item-main {
              display: flex;
              align-items: center;
              gap: 10px;
              flex: 1;
              min-width: 0;
              cursor: pointer;

              .item-icon {
                font-size: 16px;
                color: var(--el-text-color-secondary);
                flex-shrink: 0;
              }

              .item-title {
                font-size: 13px;
                color: var(--el-text-color-primary);
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
              }
            }

            .item-actions {
              flex-shrink: 0;

              .item-more {
                opacity: 0;
                transition: opacity 0.2s;

                &:hover {
                  background: var(--el-fill-color-darker);
                }
              }
            }
          }
        }
      }
    }
  }
}

/* 下拉菜单样式 */
:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;

  .el-icon {
    font-size: 14px;
  }
}
</style>
