<script setup>
import { computed, ref, watch } from 'vue'



import service from '@/api/axios'


const props = defineProps({
  schema: {
    type: Object,
    default: null,
  },
  pendingSchema: {
    type: Object,
    default: null,
  },
  schemaDiff: {
    type: Object,
    default: null,
  },
  versions: {
    type: Array,
    default: () => [],
  },
  versionsLoading: {
    type: Boolean,
    default: false,
  },
  versionError: {
    type: String,
    default: '',
  },
  operationLoading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'update:schema',
  'apply-pending',
  'cancel-pending',
  'load-versions',
  'restore-version',
])

const activeTab = ref('table')
const jsonText = ref('')
const jsonError = ref('')

const tabs = computed(() => {
  const result = [
    { key: 'table', label: '字段表格' },
    { key: 'form', label: '表单预览' },
    { key: 'json', label: 'JSON' },
    { key: 'versions', label: '版本历史' },
  ]

  if (props.pendingSchema) {
    result.push({ key: 'diff', label: '变更对比' })
  }

  return result
})

const fields = computed(() => {
  return Array.isArray(props.schema?.fields) ? props.schema.fields : []
})

function formatJson(value) {
  return JSON.stringify(value ?? {}, null, 2)
}

// AI 重新生成 Schema 时，同步到 JSON 编辑器
watch(
  () => props.schema,
  (newSchema) => {
    const newJson = formatJson(newSchema)

    // 防止用户编辑时，因为父组件更新导致光标跳动
    try {
      const currentJson = formatJson(JSON.parse(jsonText.value))

      if (currentJson === newJson) {
        return
      }
    } catch {
      // 当前文本不是合法 JSON，直接同步外部 Schema
    }

    jsonText.value = newJson
    jsonError.value = ''
  },
  {
    immediate: true,
    deep: true,
  },
)

watch(
  () => props.pendingSchema,
  (pendingSchema) => {
    if (pendingSchema) {
      activeTab.value = 'diff'
    } else if (activeTab.value === 'diff') {
      activeTab.value = 'table'
    }
  },
)

const propertyLabels = {
  entityName: '实体名称',
  entityCode: '实体编码',
  version: '版本',
  warnings: '生成提示',
  fieldName: '字段名称',
  fieldCode: '字段编码',
  dataType: '数据类型',
  required: '是否必填',
  constraints: '校验约束',
  enumOptions: '枚举选项',
}

function propertyLabel(property) {
  return propertyLabels[property] ?? property
}

function formatDiffValue(value) {
  if (value === undefined || value === null) {
    return '未设置'
  }

  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }

  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }

  return String(value)
}

function selectTab(tabKey) {
  activeTab.value = tabKey

  if (tabKey === 'versions') {
    emit('load-versions')
  }
}

function formatVersionTime(value) {
  if (!value) return ''

  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function versionSourceLabel(source) {
  const labels = {
    generate: '首次生成',
    refine: '增量修改',
    restore: '版本恢复',
    draft: '草稿保存',
  }

  return labels[source] ?? source
}

function validateSchema(schema) {
  if (!schema || typeof schema !== 'object' || Array.isArray(schema)) {
    throw new Error('Schema 必须是一个 JSON 对象')
  }

  if (!Array.isArray(schema.fields)) {
    throw new Error('Schema 中必须包含 fields 数组')
  }

  schema.fields.forEach((field, index) => {
    if (!field.fieldCode) {
      throw new Error(`第 ${index + 1} 个字段缺少 fieldCode`)
    }

    if (!field.fieldName) {
      throw new Error(`第 ${index + 1} 个字段缺少 fieldName`)
    }
  })
}



function handleJsonInput(event) {
  jsonText.value = event.target.value

  try {
    const newSchema = JSON.parse(jsonText.value)

    validateSchema(newSchema)

    jsonError.value = ''
    emit('update:schema', newSchema)
  } catch (error) {
    jsonError.value =
      error instanceof SyntaxError
        ? `JSON 格式错误：${error.message}`
        : error.message
  }
}

function inputType(field) {
  const typeMap = {
    string: 'text',
    number: 'number',
    integer: 'number',
    date: 'date',
    datetime: 'datetime-local',
    email: 'email',
    boolean: 'checkbox',
  }

  return typeMap[field?.dataType] ?? 'text'
}
// 前端界面修改后，校验修改后的schema数据
async function validateSchemaClick(schema) {
  if (!schema) {
    return
  }
  let data = await service.post('/api/schemas/validate', schema)
  if (data.status === 200) {
    console.log('schema校验成功')
  } else {
    console.log('schema校验失败')
  }
}

// 保存草稿
async function saveSchemaClick(schema) {
  if (!schema) {
    return
  }
  let data = await service.post('/api/schemas/save', schema)
  if (data.status === 200) {
    console.log('保存成功')
  } else {
    console.log('保存失败')
  }
}
</script>

<template>
  <section class="result-panel">
    <header>
      <div>
        <h2>Schema 预览</h2>
        <button @click="validateSchemaClick(schema)">校验schema信息</button>
        <button
          :disabled="Boolean(pendingSchema)"
          @click="saveSchemaClick(schema)"
        >保存草稿</button>
        <p v-if="schema">
          {{ schema.entityName }} · {{ schema.entityCode }}
        </p>
      </div>
    </header>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="selectTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div
      v-if="!schema"
      class="empty-result"
    >
      输入需求并点击“生成 Schema”后，这里会显示结果。
    </div>

    <div
      v-else
      class="tab-content"
    >
      <div v-if="activeTab === 'table'">
        <table>
          <thead>
            <tr>
              <th>字段名称</th>
              <th>字段编码</th>
              <th>类型</th>
              <th>必填</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="field in fields"
              :key="field.fieldCode"
            >
              <td>{{ field.fieldName }}</td>
              <td>{{ field.fieldCode }}</td>
              <td>{{ field.dataType }}</td>
              <td>{{ field.required ? '是' : '否' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-else-if="activeTab === 'form'"
        class="form-preview"
      >
        <label
          v-for="field in fields"
          :key="field.fieldCode"
          class="form-field"
        >
          <span>
            {{ field.fieldName }}
            <strong v-if="field.required">*</strong>
          </span>

          <select
            v-if="field.dataType === 'enum'"
            disabled
          >
            <option value="">请选择</option>
            <option
              v-for="option in field.enumOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>

          <input
            v-else
            :type="inputType(field)"
            :placeholder="`请输入${field.fieldName}`"
            disabled
          />

          <small v-if="field.constraints?.patternMessage">
            {{ field.constraints.patternMessage }}
          </small>
        </label>
      </div>

      <div
        v-else-if="activeTab === 'json'"
        class="json-editor-wrapper"
      >
  <textarea
    :value="jsonText"
    class="json-editor"
    spellcheck="false"
    @input="handleJsonInput"
  />

  <p v-if="jsonError" class="json-error">
    {{ jsonError }}
  </p>

  <p v-else class="json-success">
    JSON 格式正确，字段表格和表单预览已同步
  </p>
</div>

      <div
        v-else-if="activeTab === 'diff' && schemaDiff"
        class="diff-panel"
      >
        <div class="diff-header">
          <div>
            <h3>确认增量变更</h3>
            <p>当前 Schema 尚未修改，请检查下列差异。</p>
          </div>

          <span class="diff-total">
            {{ schemaDiff.total }} 处变更
          </span>
        </div>

        <div
          v-if="schemaDiff.total === 0"
          class="diff-empty"
        >
          模型结果与当前 Schema 一致，没有可应用的变更。
        </div>

        <section
          v-if="schemaDiff.entityChanges.length"
          class="diff-section"
        >
          <h4>实体属性修改</h4>

          <div
            v-for="change in schemaDiff.entityChanges"
            :key="change.property"
            class="property-change"
          >
            <strong>{{ propertyLabel(change.property) }}</strong>
            <div class="value-comparison">
              <pre class="before-value">{{ formatDiffValue(change.before) }}</pre>
              <span class="change-arrow">→</span>
              <pre class="after-value">{{ formatDiffValue(change.after) }}</pre>
            </div>
          </div>
        </section>

        <section
          v-if="schemaDiff.added.length"
          class="diff-section"
        >
          <h4>新增字段</h4>

          <article
            v-for="field in schemaDiff.added"
            :key="field.fieldCode"
            class="field-change added-field"
          >
            <span class="change-mark">+</span>
            <div>
              <strong>{{ field.fieldName }}</strong>
              <p>
                {{ field.fieldCode }} · {{ field.dataType }} ·
                {{ field.required ? '必填' : '非必填' }}
              </p>
            </div>
          </article>
        </section>

        <section
          v-if="schemaDiff.removed.length"
          class="diff-section"
        >
          <h4>删除字段</h4>

          <article
            v-for="field in schemaDiff.removed"
            :key="field.fieldCode"
            class="field-change removed-field"
          >
            <span class="change-mark">−</span>
            <div>
              <strong>{{ field.fieldName }}</strong>
              <p>{{ field.fieldCode }} · {{ field.dataType }}</p>
            </div>
          </article>
        </section>

        <section
          v-if="schemaDiff.modified.length"
          class="diff-section"
        >
          <h4>修改字段</h4>

          <article
            v-for="field in schemaDiff.modified"
            :key="field.fieldCode"
            class="modified-field"
          >
            <h5>{{ field.fieldName }} · {{ field.fieldCode }}</h5>

            <div
              v-for="change in field.changes"
              :key="change.property"
              class="property-change"
            >
              <strong>{{ propertyLabel(change.property) }}</strong>
              <div class="value-comparison">
                <pre class="before-value">{{ formatDiffValue(change.before) }}</pre>
                <span class="change-arrow">→</span>
                <pre class="after-value">{{ formatDiffValue(change.after) }}</pre>
              </div>
            </div>
          </article>
        </section>

        <div class="diff-actions">
          <button
            type="button"
            class="cancel-change"
            :disabled="operationLoading"
            @click="emit('cancel-pending')"
          >
            取消
          </button>
          <button
            type="button"
            class="apply-change"
            :disabled="schemaDiff.total === 0 || operationLoading"
            @click="emit('apply-pending')"
          >
            {{ operationLoading ? '正在应用…' : '应用修改' }}
          </button>
        </div>
      </div>

      <div
        v-else-if="activeTab === 'versions'"
        class="versions-panel"
      >
        <div class="versions-header">
          <div>
            <h3>版本历史</h3>
            <p>恢复旧版本会创建一个新版本，不会覆盖历史记录。</p>
          </div>

          <button
            type="button"
            class="refresh-versions"
            :disabled="versionsLoading"
            @click="emit('load-versions')"
          >
            {{ versionsLoading ? '加载中…' : '刷新' }}
          </button>
        </div>

        <p
          v-if="versionError"
          class="version-error"
        >
          {{ versionError }}
        </p>

        <div
          v-else-if="versionsLoading && versions.length === 0"
          class="version-empty"
        >
          正在加载版本历史…
        </div>

        <div
          v-else-if="versions.length === 0"
          class="version-empty"
        >
          暂无版本历史。
        </div>

        <div
          v-else
          class="version-list"
        >
          <article
            v-for="record in versions"
            :key="record.version"
            class="version-card"
            :class="{ current: record.version === schema.version }"
          >
            <div class="version-info">
              <div class="version-title">
                <strong>版本 {{ record.version }}</strong>
                <span>{{ versionSourceLabel(record.source) }}</span>
                <span
                  v-if="record.version === schema.version"
                  class="current-version"
                >
                  当前版本
                </span>
              </div>

              <p>{{ formatVersionTime(record.createdAt) }}</p>
              <p v-if="record.reason">原因：{{ record.reason }}</p>
              <p>字段数：{{ record.schema.fields.length }}</p>
            </div>

            <button
              type="button"
              class="restore-version"
              :disabled="
                record.version === schema.version ||
                Boolean(pendingSchema) ||
                operationLoading
              "
              @click="emit('restore-version', record)"
            >
              恢复此版本
            </button>
          </article>
        </div>
      </div>

      <div
        v-if="schema.warnings?.length"
        class="warnings"
      >
        <strong>生成提示</strong>
        <ul>
          <li
            v-for="warning in schema.warnings"
            :key="warning"
          >
            {{ warning }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.result-panel {
  min-width: 0;
  padding: 24px;
  overflow: auto;
  background: #f8fafc;
}

header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

header p {
  margin: 4px 0 0;
  color: #64748b;
}

.tabs {
  display: flex;
  gap: 8px;
  margin: 22px 0;
  border-bottom: 1px solid #e2e8f0;
}

.tabs button {
  padding: 9px 12px;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-bottom: 2px solid transparent;
}

.tabs button.active {
  font-weight: 600;
  color: #1677ff;
  border-bottom-color: #1677ff;
}

.empty-result {
  display: grid;
  min-height: 360px;
  color: #94a3b8;
  place-items: center;
}

table {
  width: 100%;
  overflow: hidden;
  background: #fff;
  border-collapse: collapse;
  border-radius: 8px;
}

th,
td {
  padding: 11px 12px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

th {
  color: #475569;
  background: #f1f5f9;
}

.form-preview {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
}

.form-field {
  display: block;
  margin-bottom: 18px;
}

.form-field span {
  display: block;
  margin-bottom: 6px;
}

.form-field strong {
  color: #ef4444;
}

.form-field input,
.form-field select {
  width: 100%;
  padding: 9px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
}

.form-field small {
  display: block;
  margin-top: 5px;
  color: #64748b;
}

.json-preview {
  padding: 18px;
  overflow: auto;
  color: #dbeafe;
  background: #0f172a;
  border-radius: 8px;
}

.warnings {
  padding: 12px 16px;
  margin-top: 16px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
}

.warnings ul {
  padding-left: 20px;
  margin: 6px 0 0;
}


.json-editor-wrapper {
  width: 100%;
}

.json-editor {
  box-sizing: border-box;
  width: 100%;
  min-height: 440px;
  padding: 16px;
  color: #e2e8f0;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  outline: none;
  resize: vertical;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}

.json-editor:focus {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgb(64 158 255 / 15%);
}

.json-error {
  margin: 8px 0 0;
  color: #dc2626;
  font-size: 13px;
}

.json-success {
  margin: 8px 0 0;
  color: #16a34a;
  font-size: 13px;
}

.diff-panel {
  padding: 18px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.diff-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.diff-header h3,
.diff-section h4,
.modified-field h5 {
  margin: 0;
}

.diff-header p,
.field-change p {
  margin: 5px 0 0;
  color: #64748b;
}

.diff-total {
  flex: none;
  padding: 5px 10px;
  color: #1d4ed8;
  font-size: 13px;
  background: #eff6ff;
  border-radius: 999px;
}

.diff-empty {
  padding: 24px;
  margin-top: 16px;
  color: #64748b;
  text-align: center;
  background: #f8fafc;
  border-radius: 8px;
}

.diff-section {
  margin-top: 20px;
}

.diff-section h4 {
  margin-bottom: 10px;
  color: #334155;
  font-size: 14px;
}

.field-change,
.modified-field,
.property-change {
  padding: 12px;
  margin-top: 8px;
  border-radius: 8px;
}

.field-change {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.added-field {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.removed-field {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.change-mark {
  font-size: 20px;
  font-weight: 700;
}

.added-field .change-mark {
  color: #16a34a;
}

.removed-field .change-mark {
  color: #dc2626;
}

.modified-field {
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.property-change {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.value-comparison {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  margin-top: 8px;
}

.value-comparison pre {
  min-width: 0;
  padding: 8px;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  border-radius: 6px;
}

.before-value {
  color: #991b1b;
  background: #fef2f2;
}

.after-value {
  color: #166534;
  background: #f0fdf4;
}

.change-arrow {
  color: #64748b;
}

.diff-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding-top: 18px;
  margin-top: 22px;
  border-top: 1px solid #e2e8f0;
}

.diff-actions button {
  padding: 9px 16px;
  cursor: pointer;
  border-radius: 7px;
}

.cancel-change {
  color: #475569;
  background: #fff;
  border: 1px solid #cbd5e1;
}

.apply-change {
  color: #fff;
  background: #1677ff;
  border: 1px solid #1677ff;
}

.apply-change:disabled {
  cursor: not-allowed;
  background: #94a3b8;
  border-color: #94a3b8;
}

.versions-panel {
  padding: 18px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.versions-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.versions-header h3 {
  margin: 0;
}

.versions-header p {
  margin: 5px 0 0;
  color: #64748b;
}

.refresh-versions,
.restore-version {
  flex: none;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 7px;
}

.refresh-versions {
  color: #334155;
  background: #fff;
  border: 1px solid #cbd5e1;
}

.version-list {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.version-card {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.version-card.current {
  background: #eff6ff;
  border-color: #93c5fd;
}

.version-title {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.version-title span {
  padding: 2px 7px;
  color: #475569;
  font-size: 12px;
  background: #e2e8f0;
  border-radius: 999px;
}

.version-title .current-version {
  color: #1d4ed8;
  background: #dbeafe;
}

.version-info p {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 13px;
}

.restore-version {
  color: #fff;
  background: #1677ff;
  border: 1px solid #1677ff;
}

.restore-version:disabled,
.refresh-versions:disabled,
.cancel-change:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.version-empty,
.version-error {
  padding: 24px;
  margin: 16px 0 0;
  text-align: center;
  border-radius: 8px;
}

.version-empty {
  color: #64748b;
  background: #f8fafc;
}

.version-error {
  color: #b91c1c;
  background: #fef2f2;
}
</style>
