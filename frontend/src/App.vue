<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <h1>BSV Network Sketcher</h1>
        <p>Port từ Network Sketcher gốc</p>
      </div>
      <div class="status">
        <span>Backend</span>
        <strong :class="statusClass">{{ statusText }}</strong>
      </div>
    </header>

    <section class="workspace">
      <aside class="panel left">
        <h2>Danh mục</h2>
        <ul>
          <li>Areas</li>
          <li>Devices</li>
          <li>Links</li>
        </ul>
        <button type="button" @click="fetchHealth">Kiểm tra backend</button>
      </aside>

      <main class="canvas">
        <CanvasStage />
      </main>

      <aside class="panel right">
        <h2>Inspector</h2>
        <p>Chọn một phần tử để xem chi tiết.</p>
        <div class="hint">Phase 5: Khung UI + Konva scaffold</div>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import CanvasStage from './components/CanvasStage.vue'

const statusText = ref('đang kiểm tra...')
const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const statusClass = computed(() => {
  if (statusText.value === 'healthy') return 'ok'
  if (statusText.value === 'không kết nối được') return 'error'
  if (statusText.value === 'lỗi kết nối') return 'error'
  return 'pending'
})

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
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 16px;
  padding: 20px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--panel);
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  padding: 18px 22px;
  box-shadow: var(--shadow);
}

.topbar h1 {
  font-family: 'Fraunces', serif;
  font-size: 24px;
  margin: 0;
}

.topbar p {
  margin: 6px 0 0;
  color: var(--muted);
}

.status {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status span {
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.status strong {
  font-size: 16px;
}

.status .ok {
  color: #1c7c54;
}

.status .error {
  color: #d64545;
}

.status .pending {
  color: #a26b1f;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(180px, 240px) 1fr minmax(200px, 260px);
  gap: 16px;
  min-height: 60vh;
}

.panel {
  background: var(--panel);
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  padding: 18px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel h2 {
  font-size: 16px;
  margin: 0;
}

.panel ul {
  margin: 0;
  padding: 0 0 0 18px;
  color: var(--muted);
}

.panel button {
  margin-top: auto;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 10px 14px;
  cursor: pointer;
}

.canvas {
  min-height: 60vh;
}

.hint {
  margin-top: auto;
  padding: 10px 12px;
  background: var(--accent-soft);
  border-radius: 12px;
  font-size: 13px;
}

@media (max-width: 1024px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .panel.left,
  .panel.right {
    order: 2;
  }

  .canvas {
    order: 1;
    min-height: 50vh;
  }
}
</style>
