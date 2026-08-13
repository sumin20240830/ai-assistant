<script setup>
import { computed, ref, watch } from 'vue'


const props = defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: '',
  },
  hasSchema: {
    type: Boolean,
    default: false,
  },
  task: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['generate', 'refine'])

const requirement = ref(
  '创建一个客户实体，包含姓名、手机号、客户等级、注册时间；手机号必填且需要校验，客户等级包含普通、重要、VIP 三种取值。',
)

watch(
  () => props.hasSchema,
  (hasSchema, hadSchema) => {
    if (hasSchema && !hadSchema) {
      requirement.value = ''
    }
  },
)

const canSubmit = computed(() => {
  return requirement.value.trim().length > 0 && !props.loading
})

const taskStatusLabel = computed(() => {
  const labels = {
    queued: '排队中',
    running: '模型处理中',
    validating: '校验中',
    repairing: '自动修复中',
    succeeded: '已完成',
    failed: '已失败',
  }

  return labels[props.task?.status] ?? '等待中'
})

function submit() {
  if (!canSubmit.value) return

  const content = requirement.value.trim()

  if (props.hasSchema) {
    emit('refine', content)
    return
  }

  emit('generate', content)
}
</script>

<template>
  <section class="requirement-panel">
    <header>
      <h2>{{ hasSchema ? '增量修改' : '需求描述' }}</h2>
      <p v-if="hasSchema">只描述本次需要增加、删除或修改的内容。</p>
      <p v-else>使用自然语言描述需要创建的业务实体和字段。</p>
    </header>

    <div class="empty-content">
      <div class="empty-icon">AI</div>
      <h3>描述你的业务模型</h3>
      <p>系统会把需求转换为结构化实体 Schema。</p>
    </div>

    <form
      class="input-form"
      @submit.prevent="submit"
    >
      <textarea
        v-model="requirement"
        :placeholder="hasSchema ? '例如：新增邮箱字段并设为必填……' : '例如：创建一个客户实体……'"
        :disabled="loading"
      />

      <button
        type="submit"
        :disabled="!canSubmit"
      >
        {{
          loading
            ? (hasSchema ? '正在修改…' : '正在生成…')
            : (hasSchema ? '增量修改' : '生成 Schema')
        }}
      </button>

      <div
        v-if="task"
        class="task-status"
        :class="`task-${task.status}`"
      >
        <div class="task-status-header">
          <strong>{{ taskStatusLabel }}</strong>
          <span>{{ task.progress ?? 0 }}%</span>
        </div>

        <div class="task-progress">
          <span :style="{ width: `${task.progress ?? 0}%` }" />
        </div>

        <p>{{ task.message }}</p>
        <small v-if="task.repairAttempt">
          已进行第 {{ task.repairAttempt }} 次自动修复
        </small>
      </div>

      <p v-if="error" class="generate-error">
        {{ error }}
      </p>
    </form>
  </section>
</template>

<style scoped>
.requirement-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 24px;
  background: #fff;
  border-right: 1px solid #e5e7eb;
}

header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

header p,
.empty-content p {
  margin: 6px 0 0;
  color: #64748b;
}

.empty-content {
  display: grid;
  flex: 1;
  place-content: center;
  text-align: center;
}

.empty-icon {
  display: grid;
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  font-weight: 700;
  color: #1677ff;
  place-items: center;
  background: #eaf3ff;
  border-radius: 16px;
}

.empty-content h3 {
  margin: 0;
  font-weight: 600;
}

.input-form {
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

textarea {
  width: 100%;
  min-height: 130px;
  padding: 12px;
  resize: vertical;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  outline: none;
}

textarea:focus {
  border-color: #1677ff;
}

.input-form button {
  width: 100%;
  padding: 11px;
  margin-top: 12px;
  color: #fff;
  cursor: pointer;
  background: #1677ff;
  border: 0;
  border-radius: 8px;
}

.input-form button:disabled {
  cursor: not-allowed;
  background: #94a3b8;
}

.generate-error {
  padding: 10px 12px;
  margin: 10px 0 0;
  color: #b91c1c;
  font-size: 13px;
  line-height: 1.5;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
}

.task-status {
  padding: 12px;
  margin-top: 12px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

.task-status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.task-status p {
  margin: 8px 0 0;
  font-size: 13px;
}

.task-status small {
  display: block;
  margin-top: 5px;
  color: #92400e;
}

.task-progress {
  height: 6px;
  margin-top: 9px;
  overflow: hidden;
  background: #e2e8f0;
  border-radius: 999px;
}

.task-progress span {
  display: block;
  height: 100%;
  background: #1677ff;
  border-radius: inherit;
  transition: width 0.25s ease;
}

.task-repairing {
  background: #fffbeb;
  border-color: #fde68a;
}

.task-succeeded {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.task-succeeded .task-progress span {
  background: #16a34a;
}

.task-failed {
  color: #991b1b;
  background: #fef2f2;
  border-color: #fecaca;
}

.task-failed .task-progress span {
  background: #dc2626;
}
</style>
