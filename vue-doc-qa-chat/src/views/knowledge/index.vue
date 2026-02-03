<script setup lang="ts">
import { Search, RefreshRight, View, EditPen, Delete, QuestionFilled, Loading } from '@element-plus/icons-vue'
import { onMounted, ref, reactive, toRaw, markRaw, computed, onUnmounted } from 'vue'
import { docPageApi, docDeleteApi, createVectorStreamConnection } from '@/api/documents'
import type { DocParamsType, DocTableType, VectorProgressType } from '@/api/documents/types'
import writeForm from './writeForm.vue'

const loading = ref(false)
const tableLoadText = ref('加载中……')

// 向量化进度状态
const vectorizing = ref(false)
const vectorProgress = ref<VectorProgressType>({
  status: 'idle',
  current: 0,
  total: 0,
  message: '',
  error: null,
  elapsed: 0,
  batch_current: 0,
  batch_total: 0,
  progress: 0
})
let eventSource: EventSource | null = null

// 进度显示文本
const progressText = computed(() => {
  const p = vectorProgress.value
  if (p.status === 'idle') return ''
  if (p.status === 'loading') return p.message || '正在加载文档...'
  if (p.status === 'splitting') return p.message || '正在分割文档...'
  if (p.status === 'vectorizing') {
    if (p.total > 0) {
      return `${p.message} (${p.current}/${p.total})`
    }
    return p.message || '正在向量化...'
  }
  if (p.status === 'completed') return '构建完成！'
  if (p.status === 'error') return `失败：${p.error || p.message}`
  return p.message
})

// 状态颜色
const progressStatus = computed(() => {
  const status = vectorProgress.value.status
  if (status === 'completed') return 'success'
  if (status === 'error') return 'exception'
  return ''
})

/** 添加/编辑弹窗表单 */
const dialog = reactive({
  writeFormVisible: false
})
const searchForm = reactive({
  name: ''
})
const tableState = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0
})
const tableDataList = ref<DocTableType[]>([])

// 选中当前行数据
let currentRow: DocTableType | null = null

onMounted(() => {
  // 页面加载完成时就调用获取一次table数据
  getTableList()
})

onUnmounted(() => {
  // 组件卸载时关闭 SSE 连接
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})

/**
 * 获取表格数据
 * @param params 页码参数
 */
async function getTableList(params?: DocParamsType) {
  loading.value = true

  const res = await docPageApi(params || { page_num: 1, page_size: 10 }).finally(() => (loading.value = false))
  tableState.pageNum = res.data.page_num
  tableState.pageSize = res.data.page_size
  tableState.total = res.data.total
  tableDataList.value = res.data.list
}

/**
 * 重新加载表格
 */
const reloadTable = () => {
  const params: DocParamsType = {
    page_num: tableState.pageNum,
    page_size: tableState.pageSize
  }
  getTableList(params)
}

const onSearch = () => {
  const params: DocParamsType = {
    page_num: 1,
    page_size: tableState.pageSize,
    name: searchForm.name
  }
  getTableList(params)
}

const onSearchReset = () => {
  searchForm.name = ''
}

const onAdd = () => {
  dialog.writeFormVisible = true
  currentRow = null
}

const onEdit = (index: number, row: DocTableType) => {
  dialog.writeFormVisible = true
  currentRow = toRaw(row)
}

const onDeleteRow = async (index: number, row: DocTableType) => {
  loading.value = true
  await docDeleteApi(row.id).finally(() => (loading.value = false))
  ElMessage.success('删除成功！')
  reloadTable()

  ElMessageBox.confirm('删除文件后，向量数据库还存在该文件的向量化数据。是否重新构建知识库？', '删除成功！是否重新构建？', {
    type: 'info',
    icon: markRaw(QuestionFilled)
  })
    .then(() => {
      vectorAll()
    })
    .catch(() => {})
}

/**
 * 知识库向量化事件
 */
const onVectorClick = async () => {
  if (tableDataList.value.length === 0) {
    ElMessage.warning('请先上传文档。')
    return
  }

  ElMessageBox.confirm('确定要将所有文档向量化并构建知识库吗？', '构建知识库？', {
    type: 'info',
    icon: markRaw(QuestionFilled)
  })
    .then(async () => {
      vectorAll()
    })
    .catch(() => {})
}

/**
 * 知识库向量化操作（使用 SSE 获取进度）
 */
async function vectorAll() {
  vectorizing.value = true
  vectorProgress.value = {
    status: 'loading',
    current: 0,
    total: 0,
    message: '正在连接服务器...',
    error: null,
    elapsed: 0,
    batch_current: 0,
    batch_total: 0,
    progress: 0
  }

  // 关闭之前的连接
  if (eventSource) {
    eventSource.close()
  }

  // 创建 SSE 连接
  eventSource = createVectorStreamConnection(
    // 进度回调
    (data: VectorProgressType) => {
      vectorProgress.value = data
      console.log('向量化进度:', data)
    },
    // 完成回调
    () => {
      vectorizing.value = false
      if (vectorProgress.value.status === 'completed') {
        ElMessage.success('知识库构建完成！')
      } else if (vectorProgress.value.status === 'error') {
        ElMessageBox.alert(
          vectorProgress.value.error || vectorProgress.value.message || '未知错误',
          '构建失败！',
          {
            type: 'error',
            customStyle: {
              'max-height': '500px',
              'max-width': '50%',
              width: 'auto',
              overflow: 'auto'
            }
          }
        )
      }
      reloadTable()
      eventSource = null
    },
    // 错误回调
    (error: Error) => {
      vectorizing.value = false
      vectorProgress.value.status = 'error'
      vectorProgress.value.error = error.message
      ElMessage.error(`连接错误：${error.message}`)
      eventSource = null
    }
  )
}

/**
 * 表单弹窗提交成功回调
 */
const onOk = () => {
  reloadTable()
}
</script>

<template>
  <div class="main-full upload-box">
    <div class="card search-card">
      <el-form :inline="true" :model="searchForm" class="search-form-inline">
        <el-form-item label="文档名称">
          <el-input v-model="searchForm.name" placeholder="请输入文档名称……" clearable />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :icon="Search" :loading="loading" @click="onSearch">查询</el-button>
          <el-button :icon="RefreshRight" :loading="loading" @click="onSearchReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="card table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="onAdd">上传文档</el-button>
          <el-button
            type="success"
            :disabled="tableDataList.length === 0 || vectorizing"
            :loading="vectorizing"
            @click="onVectorClick()"
          >
            {{ vectorizing ? '构建中...' : '构建知识库' }}
          </el-button>
        </div>

        <!-- 向量化进度条 -->
        <div v-if="vectorizing || vectorProgress.status === 'completed' || vectorProgress.status === 'error'" class="progress-container">
          <div class="progress-info">
            <span class="progress-text">{{ progressText }}</span>
            <span v-if="vectorProgress.elapsed > 0" class="progress-time">
              {{ Math.floor(vectorProgress.elapsed / 60) }}:{{ String(Math.floor(vectorProgress.elapsed % 60)).padStart(2, '0') }}
            </span>
          </div>
          <el-progress
            :percentage="vectorProgress.progress"
            :status="progressStatus"
            :stroke-width="12"
            :show-text="false"
          />
          <div v-if="vectorProgress.batch_total > 0" class="progress-batch">
            批次: {{ vectorProgress.batch_current }}/{{ vectorProgress.batch_total }}
          </div>
        </div>
      </div>

      <el-table :data="tableDataList" v-loading="loading" :element-loading-text="tableLoadText" :border="true" class="table-main">
        <el-table-column type="index" align="center" label="序号" width="60" />
        <el-table-column prop="name" align="center" label="文档名称">
          <template #default="scope">
            <el-link type="primary" :href="'/api/documents/read/' + scope.row.id" target="_blank">
              {{ scope.row.name }}
            </el-link>
          </template>
        </el-table-column>

        <el-table-column prop="suffix" align="center" label="格式" width="100" />

        <el-table-column prop="vector" align="center" label="知识库状态" width="150">
          <template #default="scope">
            <el-tag v-if="scope.row.vector === 'yes'" type="success">已构建</el-tag>
            <el-tag v-else type="info">未构建</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="date" align="center" label="上传时间" width="200" />
        <el-table-column align="center" label="操作" width="200">
          <template #default="scope">
            <el-button type="primary" link>
              <el-link type="primary" :underline="false" :icon="View" :href="'/api/documents/read/' + scope.row.id" target="_blank">
                查看
              </el-link>
            </el-button>
            <el-button type="primary" link :icon="EditPen" @click="onEdit(scope.$index, scope.row)">编辑</el-button>
            <el-popconfirm title="确定要删除该文档吗？" width="180" placement="top-end" @confirm="onDeleteRow(scope.$index, scope.row)">
              <template #reference>
                <el-button type="danger" link :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无文档，请上传文档构建知识库" :image-size="100" />
        </template>
      </el-table>

      <el-pagination
        v-model:current-page="tableState.pageNum"
        v-model:page-size="tableState.pageSize"
        :page-sizes="[10, 20, 30, 40, 50]"
        :background="true"
        layout="total, sizes, prev, pager, next, jumper"
        :total="tableState.total"
        class="pagination-right"
      />
    </div>

    <write-form
      v-if="dialog.writeFormVisible"
      :open="dialog.writeFormVisible"
      :current-row="currentRow"
      @ok="onOk"
      @closed="closed => (dialog.writeFormVisible = closed)"
    />
  </div>
</template>

<style lang="scss" scoped>
.upload-box {
  display: flex;
  flex-direction: column;

  .search-card {
    padding: 18px 18px 0;
    margin-bottom: 10px;

    .search-form-inline {
      .el-input {
        --el-input-width: 220px;
      }
    }
  }

  .table-card {
    display: flex;
    flex: 1;
    flex-direction: column;
    width: 100%;

    .table-toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 10px;

      .toolbar-left {
        display: flex;
        gap: 8px;
      }

      .progress-container {
        display: flex;
        flex: 1;
        flex-direction: column;
        gap: 6px;
        min-width: 300px;
        max-width: 500px;
        padding: 12px 16px;
        background: var(--el-fill-color-light);
        border-radius: 8px;

        .progress-info {
          display: flex;
          gap: 12px;
          align-items: center;
          justify-content: space-between;

          .progress-text {
            flex: 1;
            font-size: 13px;
            color: var(--el-text-color-regular);
          }

          .progress-time {
            font-family: monospace;
            font-size: 12px;
            color: var(--el-text-color-secondary);
          }
        }

        .progress-batch {
          font-size: 12px;
          color: var(--el-text-color-secondary);
          text-align: right;
        }
      }
    }

    .table-main {
      flex: 1;
      width: 100%;
    }
  }
}
</style>
