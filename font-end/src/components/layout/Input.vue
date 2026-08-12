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
</style>
