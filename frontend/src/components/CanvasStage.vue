<template>
  <div ref="containerRef" class="canvas-shell">
    <v-stage :config="stageConfig">
      <v-layer>
        <v-rect :config="gridConfig" />
        <v-text :config="labelConfig" />
      </v-layer>
    </v-stage>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const containerRef = ref<HTMLDivElement | null>(null)
const stageSize = ref({ width: 300, height: 200 })
let observer: ResizeObserver | null = null

const stageConfig = computed(() => ({
  width: stageSize.value.width,
  height: stageSize.value.height
}))

const gridConfig = computed(() => ({
  x: 16,
  y: 16,
  width: Math.max(stageSize.value.width - 32, 0),
  height: Math.max(stageSize.value.height - 32, 0),
  stroke: '#d0c6bc',
  strokeWidth: 1,
  dash: [8, 6],
  cornerRadius: 12
}))

const labelConfig = computed(() => ({
  x: 32,
  y: 32,
  text: 'Canvas Konva (placeholder)',
  fontSize: 16,
  fill: '#5a524b'
}))

function updateSize() {
  const el = containerRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  stageSize.value = {
    width: Math.max(Math.floor(rect.width), 0),
    height: Math.max(Math.floor(rect.height), 0)
  }
}

onMounted(() => {
  updateSize()
  observer = new ResizeObserver(() => updateSize())
  if (containerRef.value) {
    observer.observe(containerRef.value)
  }
})

onBeforeUnmount(() => {
  if (observer && containerRef.value) {
    observer.unobserve(containerRef.value)
  }
  observer = null
})
</script>

<style scoped>
.canvas-shell {
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at 20% 20%, #fff7f2 0%, #ffffff 42%, #f6f1ea 100%);
  border-radius: 18px;
  border: 1px solid rgba(28, 28, 28, 0.08);
  box-shadow: var(--shadow);
  overflow: hidden;
}
</style>
