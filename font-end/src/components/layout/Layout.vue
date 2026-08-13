<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import Session from './Session.vue'
import RequirementInput from './Input.vue'
import SchemaResult from './Result.vue'
import service from '@/api/axios'
import { diffSchemas } from '@/utils/schemaDiff'

const sessions = ref([
  { id: 'session-001', title: '客户实体建模' },
  { id: 'session-002', title: '订单实体建模' },
])

const activeSessionId = ref('session-001')
const schema = ref(null)
const pendingSchema = ref(null)
const pendingSource = ref(null)
const pendingReason = ref('')
const versionHistory = ref([])
const versionLoading = ref(false)
const versionError = ref('')
const loading = ref(false)
const generationError = ref('')
const taskState = ref(null)
let taskRunId = 0

const schemaDiff = computed(() => {
  if (!schema.value || !pendingSchema.value) {
    return null
  }

  return diffSchemas(schema.value, pendingSchema.value)
})

const customerSchema = {
  entityName: '客户',
  entityCode: 'Customer',
  version: 1,
  fields: [
    {
      fieldName: '姓名',
      fieldCode: 'name',
      dataType: 'string',
      required: false,
    },
    {
      fieldName: '手机号',
      fieldCode: 'mobile',
      dataType: 'string',
      required: true,
      constraints: {
        pattern: '^1[3-9]\\d{9}$',
        patternMessage: '请输入有效的手机号',
      },
    },
    {
      fieldName: '客户等级',
      fieldCode: 'customerLevel',
      dataType: 'enum',
      required: false,
      enumOptions: [
        { label: '普通', value: 'NORMAL' },
        { label: '重要', value: 'IMPORTANT' },
        { label: 'VIP', value: 'VIP' },
      ],
    },
    {
      fieldName: '注册时间',
      fieldCode: 'registeredAt',
      dataType: 'datetime',
      required: false,
    },
  ],
  warnings: ['用户未说明姓名是否必填，当前按非必填处理'],
}

async function selectSession(sessionId) {
  taskRunId += 1
  taskState.value = null
  loading.value = false
  activeSessionId.value = sessionId
  pendingSchema.value = null
  pendingSource.value = null
  pendingReason.value = ''
  generationError.value = ''
  await loadVersions(true)
}

function createSession() {
  taskRunId += 1
  taskState.value = null
  loading.value = false
  const id = crypto.randomUUID()

  sessions.value.unshift({
    id,
    title: '新建会话',
  })

  activeSessionId.value = id
  schema.value = null
  pendingSchema.value = null
  pendingSource.value = null
  pendingReason.value = ''
  versionHistory.value = []
  versionError.value = ''
}

async function createVersion(
  schemaData,
  source,
  reason = '',
  sessionId = activeSessionId.value,
) {
  const response = await service.post('/api/schema-versions', {
    sessionId,
    schema: schemaData,
    source,
    reason: reason || null,
  })

  return response.data
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

async function runSchemaTask(payload) {
  const runId = ++taskRunId
  const response = await service.post('/api/schema-tasks', payload)
  const taskId = response.data.taskId

  taskState.value = {
    taskId,
    status: response.data.status,
    message: '任务已提交，等待处理',
    progress: 0,
    repairAttempt: 0,
  }

  while (runId === taskRunId) {
    await wait(800)

    if (runId !== taskRunId) {
      return null
    }

    const taskResponse = await service.get(`/api/schema-tasks/${taskId}`)
    const task = taskResponse.data
    taskState.value = task

    if (task.status === 'succeeded') {
      return task.result
    }

    if (task.status === 'failed') {
      const taskError = new Error(task.message || '任务执行失败')
      taskError.task = task
      throw taskError
    }
  }

  return null
}

async function loadVersions(useLatestSchema = false) {
  const sessionId = activeSessionId.value
  versionLoading.value = true
  versionError.value = ''

  try {
    const response = await service.get(`/api/schema-versions/${sessionId}`)

    if (sessionId !== activeSessionId.value) return

    versionHistory.value = response.data

    if (useLatestSchema) {
      schema.value = response.data[0]?.schema ?? null
    }
  } catch (error) {
    versionError.value =
      error.response?.data?.detail ||
      error.message ||
      '加载版本历史失败'
  } finally {
    if (sessionId === activeSessionId.value) {
      versionLoading.value = false
    }
  }
}

async function generateSchema(requirement) {
  const sessionId = activeSessionId.value
  loading.value = true
  generationError.value = ''

  try {
    const result = await runSchemaTask({
      type: 'generate',
      requirement,
    })

    if (!result || sessionId !== activeSessionId.value) return

    const record = await createVersion(
      result,
      'generate',
      '根据用户需求首次生成',
      sessionId,
    )

    schema.value = record.schema
    pendingSchema.value = null
    pendingSource.value = null
    pendingReason.value = ''
    await loadVersions()
  } catch (error) {
    const detail = error.response?.data?.detail

    generationError.value =
      (typeof detail === 'string' ? detail : detail?.message) ||
      error.message ||
      '生成 Schema 失败，请稍后重试'

    console.error('生成 Schema 失败：', detail || error)
  } finally {
    loading.value = false
  }
}

async function refineSchema(instruction) {
  if (!schema.value) {
    generationError.value = '请先生成 Schema'
    return
  }

  if (pendingSchema.value) {
    generationError.value = '请先应用或取消当前待确认的变更'
    return
  }

  loading.value = true
  generationError.value = ''
  const sessionId = activeSessionId.value

  try {
    const result = await runSchemaTask({
      type: 'refine',
      instruction,
      currentSchema: schema.value,
    })

    if (!result || sessionId !== activeSessionId.value) return

    // 先作为候选结果用于 Diff，用户确认前不覆盖当前 Schema。
    pendingSchema.value = result
    pendingSource.value = 'refine'
    pendingReason.value = instruction
  } catch (error) {
    const detail = error.response?.data?.detail

    generationError.value =
      (typeof detail === 'string' ? detail : detail?.message) ||
      error.message ||
      '增量修改失败，请稍后重试'

    console.error('增量修改失败：', detail || error)
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  taskRunId += 1
})

async function applyPendingSchema() {
  if (!pendingSchema.value) return
  
  loading.value = true
  generationError.value = ''

  try {
    const record = await createVersion(
      JSON.parse(JSON.stringify(pendingSchema.value)),
      pendingSource.value ?? 'refine',
      pendingReason.value,
    )

    schema.value = record.schema
    pendingSchema.value = null
    pendingSource.value = null
    pendingReason.value = ''
    await loadVersions()
  } catch (error) {
    const detail = error.response?.data?.detail

    generationError.value =
      (typeof detail === 'string' ? detail : detail?.message) ||
      error.message ||
      '应用修改失败'
  } finally {
    loading.value = false
  }
}

function cancelPendingSchema() {
  pendingSchema.value = null
  pendingSource.value = null
  pendingReason.value = ''
}

function restoreVersion(record) {
  if (!schema.value || pendingSchema.value) return

  const restoredSchema = JSON.parse(JSON.stringify(record.schema))
  restoredSchema.version = schema.value.version + 1
  restoredSchema.warnings = [
    ...(restoredSchema.warnings ?? []),
    `本候选版本由版本 ${record.version} 恢复`,
  ]

  pendingSchema.value = restoredSchema
  pendingSource.value = 'restore'
  pendingReason.value = `恢复版本 ${record.version}`
}
</script>

<template>
  <main class="modeling-layout">
    <Session
      :sessions="sessions"
      :active-session-id="activeSessionId"
      @select="selectSession"
      @create="createSession"
    />

    <RequirementInput
      :loading="loading"
      :error="generationError"
      :task="taskState"
      :has-schema="Boolean(schema)"
      @generate="generateSchema"
      @refine="refineSchema"
    />

    <SchemaResult
      v-model:schema="schema"
      :pending-schema="pendingSchema"
      :schema-diff="schemaDiff"
      :versions="versionHistory"
      :versions-loading="versionLoading"
      :version-error="versionError"
      :operation-loading="loading"
      @apply-pending="applyPendingSchema"
      @cancel-pending="cancelPendingSchema"
      @load-versions="loadVersions"
      @restore-version="restoreVersion"
    />
  </main>
</template>

<style scoped>
.modeling-layout {
  display: grid;
  grid-template-columns:
    240px
    minmax(320px, 1fr)
    minmax(420px, 1.2fr);
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: #f5f7fa;
}

@media (max-width: 1100px) {
  .modeling-layout {
    grid-template-columns: 220px 1fr;
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .modeling-layout > :last-child {
    grid-column: 1 / -1;
  }
}
</style>
