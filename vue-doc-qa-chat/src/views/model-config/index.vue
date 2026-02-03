<script setup lang="ts">
import { Plus, Edit, Delete, Check } from '@element-plus/icons-vue'
import { onMounted, ref, reactive, markRaw } from 'vue'
import {
  modelConfigListApi,
  modelConfigAddApi,
  modelConfigUpdateApi,
  modelConfigDeleteApi,
  modelConfigSetActiveApi
} from '@/api/model-config'
import type { ModelConfigType, ModelConfigCreateType, ModelConfigUpdateType } from '@/api/model-config/types'

const loading = ref(false)

/** 聊天模型配置列表 */
const chatConfigList = ref<ModelConfigType[]>([])
/** 向量化模型配置列表 */
const embeddingConfigList = ref<ModelConfigType[]>([])

/** 弹窗状态 */
const dialogVisible = ref(false)
const dialogTitle = ref('添加模型配置')
const isEdit = ref(false)
const currentEditId = ref('')

/** 表单数据 */
const formData = reactive<ModelConfigCreateType>({
  config_type: 'chat',
  model_name: '',
  api_key: '',
  base_url: '',
  is_active: false,
  remark: ''
})

const formRules = {
  config_type: [{ required: true, message: '请选择配置类型', trigger: 'change' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入 API Key', trigger: 'blur' }],
  base_url: [{ required: true, message: '请输入 API 地址', trigger: 'blur' }]
}

const formRef = ref()

onMounted(() => {
  loadConfigList()
})

/** 加载配置列表 */
async function loadConfigList() {
  loading.value = true
  try {
    const res = await modelConfigListApi()
    const allConfigs = res.data
    chatConfigList.value = allConfigs.filter((c) => c.config_type === 'chat')
    embeddingConfigList.value = allConfigs.filter((c) => c.config_type === 'embedding')
  } catch (error) {
    console.error('加载配置失败', error)
  } finally {
    loading.value = false
  }
}

/** 打开添加弹窗 */
function onAdd(configType: 'chat' | 'embedding') {
  isEdit.value = false
  dialogTitle.value = configType === 'chat' ? '添加聊天模型配置' : '添加向量化模型配置'
  resetForm()
  formData.config_type = configType
  dialogVisible.value = true
}

/** 打开编辑弹窗 */
function onEdit(row: ModelConfigType) {
  isEdit.value = true
  currentEditId.value = row.id
  dialogTitle.value = row.config_type === 'chat' ? '编辑聊天模型配置' : '编辑向量化模型配置'
  Object.assign(formData, {
    config_type: row.config_type,
    model_name: row.model_name,
    api_key: row.api_key,
    base_url: row.base_url,
    is_active: row.is_active,
    remark: row.remark || ''
  })
  dialogVisible.value = true
}

/** 删除配置 */
async function onDelete(row: ModelConfigType) {
  loading.value = true
  try {
    await modelConfigDeleteApi(row.id)
    ElMessage.success('删除成功')
    loadConfigList()
  } catch (error) {
    console.error('删除失败', error)
  } finally {
    loading.value = false
  }
}

/** 设置为启用 */
async function onSetActive(row: ModelConfigType) {
  loading.value = true
  try {
    await modelConfigSetActiveApi(row.id)
    ElMessage.success('设置成功')
    loadConfigList()
  } catch (error) {
    console.error('设置失败', error)
  } finally {
    loading.value = false
  }
}

/** 提交表单 */
async function onSubmit() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return

    loading.value = true
    try {
      if (isEdit.value) {
        const updateData: ModelConfigUpdateType = { ...formData }
        await modelConfigUpdateApi(currentEditId.value, updateData)
        ElMessage.success('更新成功')
      } else {
        await modelConfigAddApi(formData)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      loadConfigList()
    } catch (error) {
      console.error('操作失败', error)
    } finally {
      loading.value = false
    }
  })
}

/** 重置表单 */
function resetForm() {
  formData.config_type = 'chat'
  formData.model_name = ''
  formData.api_key = ''
  formData.base_url = ''
  formData.is_active = false
  formData.remark = ''
}

/** 弹窗关闭 */
function onDialogClosed() {
  formRef.value?.resetFields()
}
</script>

<template>
  <div class="main-full model-config-box">
    <!-- 聊天模型配置 -->
    <div class="card config-card">
      <div class="card-header">
        <h3>聊天模型配置</h3>
        <el-button type="primary" :icon="Plus" @click="onAdd('chat')">添加</el-button>
      </div>

      <el-table :data="chatConfigList" v-loading="loading" :border="true" class="table-main">
        <el-table-column prop="model_name" label="模型名称" min-width="150" />
        <el-table-column prop="base_url" label="API 地址" min-width="300" show-overflow-tooltip />
        <el-table-column prop="api_key" label="API Key" min-width="200" show-overflow-tooltip>
          <template #default="scope">
            <span>{{ scope.row.api_key.substring(0, 10) }}****</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag v-if="scope.row.is_active" type="success">启用中</el-tag>
            <el-tag v-else type="info">未启用</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="scope">
            <el-button
              v-if="!scope.row.is_active"
              type="success"
              link
              :icon="Check"
              @click="onSetActive(scope.row)"
            >
              启用
            </el-button>
            <el-button type="primary" link :icon="Edit" @click="onEdit(scope.row)">编辑</el-button>
            <el-popconfirm title="确定要删除该配置吗？" width="200" @confirm="onDelete(scope.row)">
              <template #reference>
                <el-button type="danger" link :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :image-size="60" description="暂无聊天模型配置" />
        </template>
      </el-table>
    </div>

    <!-- 向量化模型配置 -->
    <div class="card config-card">
      <div class="card-header">
        <h3>向量化模型配置</h3>
        <el-button type="primary" :icon="Plus" @click="onAdd('embedding')">添加</el-button>
      </div>

      <el-table :data="embeddingConfigList" v-loading="loading" :border="true" class="table-main">
        <el-table-column prop="model_name" label="模型名称" min-width="150" />
        <el-table-column prop="base_url" label="API 地址" min-width="300" show-overflow-tooltip />
        <el-table-column prop="api_key" label="API Key" min-width="200" show-overflow-tooltip>
          <template #default="scope">
            <span>{{ scope.row.api_key.substring(0, 10) }}****</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag v-if="scope.row.is_active" type="success">启用中</el-tag>
            <el-tag v-else type="info">未启用</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="scope">
            <el-button
              v-if="!scope.row.is_active"
              type="success"
              link
              :icon="Check"
              @click="onSetActive(scope.row)"
            >
              启用
            </el-button>
            <el-button type="primary" link :icon="Edit" @click="onEdit(scope.row)">编辑</el-button>
            <el-popconfirm title="确定要删除该配置吗？" width="200" @confirm="onDelete(scope.row)">
              <template #reference>
                <el-button type="danger" link :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :image-size="60" description="暂无向量化模型配置" />
        </template>
      </el-table>
    </div>

    <!-- 添加/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      :close-on-click-modal="false"
      @closed="onDialogClosed"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-form-item label="配置类型" prop="config_type">
          <el-select v-model="formData.config_type" placeholder="请选择配置类型" :disabled="isEdit">
            <el-option label="聊天模型" value="chat" />
            <el-option label="向量化模型" value="embedding" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称" prop="model_name">
          <el-input v-model="formData.model_name" placeholder="例如: qwen-turbo, text-embedding-v3" />
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="formData.api_key" placeholder="请输入 API Key" show-password />
        </el-form-item>
        <el-form-item label="API 地址" prop="base_url">
          <el-input v-model="formData.base_url" placeholder="例如: https://dashscope.aliyuncs.com/compatible-mode/v1" />
        </el-form-item>
        <el-form-item label="立即启用">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="formData.remark" type="textarea" placeholder="可选备注" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="onSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.model-config-box {
  display: flex;
  flex-direction: column;
  gap: 16px;

  .config-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;

      h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
      }
    }

    .table-main {
      width: 100%;
    }
  }
}
</style>
