<script setup>
defineProps({
  sessions: {
    type: Array,
    default: () => [],
  },
  activeSessionId: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['select', 'create'])
</script>

<template>
  <aside class="session-panel">
    <div class="session-header">
      <h1>AI 建模助手</h1>

      <button
        type="button"
        class="create-button"
        @click="emit('create')"
      >
        ＋ 新建会话
      </button>
    </div>

    <ul class="session-list">
      <li
        v-for="session in sessions"
        :key="session.id"
      >
        <button
          type="button"
          class="session-item"
          :class="{ active: session.id === activeSessionId }"
          @click="emit('select', session.id)"
        >
          {{ session.title }}
        </button>
      </li>
    </ul>
  </aside>
</template>

<style scoped>
.session-panel {
  min-width: 0;
  padding: 20px 14px;
  overflow-y: auto;
  color: #fff;
  background: #182230;
}

.session-header h1 {
  margin: 0 8px 20px;
  font-size: 18px;
  font-weight: 600;
}

.create-button {
  width: 100%;
  padding: 10px 12px;
  color: #fff;
  cursor: pointer;
  background: #1677ff;
  border: 0;
  border-radius: 8px;
}

.session-list {
  padding: 0;
  margin: 18px 0 0;
  list-style: none;
}

.session-item {
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 6px;
  overflow: hidden;
  color: #cbd5e1;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 8px;
}

.session-item:hover,
.session-item.active {
  color: #fff;
  background: #334155;
}
</style>