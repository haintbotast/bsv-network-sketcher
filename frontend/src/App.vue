<template>
  <main class="wrap">
    <h1>BSV Network Sketcher</h1>
    <p class="note">Port từ Network Sketcher gốc.</p>
    <p>Trạng thái backend: <strong>{{ statusText }}</strong></p>
    <button type="button" @click="fetchHealth">Kiểm tra lại</button>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const statusText = ref('đang kiểm tra...')
const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

async function fetchHealth() {
  try {
    const res = await fetch(`${apiBase}/api/v1/health`)
    if (!res.ok) {
      statusText.value = 'lỗi kết nối'
      return
    }
    const data = await res.json()
    statusText.value = data.status ?? 'không xác định'
  } catch {
    statusText.value = 'không kết nối được'
  }
}

fetchHealth()
</script>

<style scoped>
.wrap {
  font-family: system-ui, sans-serif;
  padding: 24px;
}

.note {
  color: #666;
  margin: 4px 0 12px;
}
</style>
