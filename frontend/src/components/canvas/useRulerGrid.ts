import { computed, type Ref, type ComputedRef } from 'vue'
import type { Viewport } from '../../models/types'
import { GRID_CELL_UNITS, colIndexToLetters } from '../../utils/excelGrid'
import { UNIT_PX } from '../../composables/canvasConstants'

export const RULER_H_HEIGHT = 24
export const RULER_V_WIDTH = 36

const CELL_PX = GRID_CELL_UNITS * UNIT_PX // 30px logical per cell

const RULER_BG = '#faf8f5'
const RULER_BORDER = '#d0c6bc'
const RULER_TICK = '#c0b8ae'
const RULER_LABEL = '#8a8078'
const RULER_FONT = '10px Inter, system-ui, sans-serif'

const GRID_MINOR_STROKE = '#f0ece8'
const GRID_MAJOR_STROKE = '#e0dbd4'

export function useRulerGrid(params: {
  viewport: Ref<Viewport> | ComputedRef<Viewport>
  stageSize: Ref<{ width: number; height: number }>
  showRulers: Ref<boolean> | ComputedRef<boolean>
  showGridLines: Ref<boolean> | ComputedRef<boolean>
}) {
  const { viewport, stageSize, showRulers, showGridLines } = params

  const labelStep = computed(() => {
    const cellPx = CELL_PX * viewport.value.scale
    if (cellPx >= 40) return 1
    if (cellPx >= 20) return 4
    if (cellPx >= 10) return 8
    return 16
  })

  // Visible bounds in logical pixels (same coords as Konva shapes)
  const visibleBounds = computed(() => {
    const { scale, offsetX, offsetY } = viewport.value
    const { width, height } = stageSize.value
    const left = -offsetX / scale
    const top = -offsetY / scale
    const right = (width - offsetX) / scale
    const bottom = (height - offsetY) / scale
    return { left, top, right, bottom }
  })

  // --- Ruler drawing (HTML Canvas 2D) ---

  function drawHRuler(ctx: CanvasRenderingContext2D, canvasWidth: number, canvasHeight: number, panOffsetX = 0) {
    const dpr = window.devicePixelRatio || 1
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, canvasWidth, canvasHeight)
    ctx.fillStyle = RULER_BG
    ctx.fillRect(0, 0, canvasWidth, canvasHeight)

    const { scale } = viewport.value
    const offsetX = viewport.value.offsetX + panOffsetX
    const cellPx = CELL_PX * scale
    const step = labelStep.value

    const firstCol = Math.max(1, Math.floor(-offsetX / cellPx) + 1)
    const lastCol = Math.ceil((canvasWidth - offsetX) / cellPx) + 1

    ctx.font = RULER_FONT
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    for (let col = firstCol; col <= lastCol; col++) {
      const x = (col - 1) * cellPx + offsetX
      if (x < -cellPx || x > canvasWidth + cellPx) continue

      const isMajor = (col - 1) % 4 === 0
      const tickH = isMajor ? 7 : 3

      // Tick
      ctx.strokeStyle = RULER_TICK
      ctx.lineWidth = isMajor ? 1 : 0.5
      ctx.beginPath()
      ctx.moveTo(x, canvasHeight - tickH)
      ctx.lineTo(x, canvasHeight)
      ctx.stroke()

      // Label at step intervals
      if ((col - 1) % step === 0) {
        ctx.fillStyle = RULER_LABEL
        ctx.fillText(colIndexToLetters(col), x + cellPx * 0.5, canvasHeight * 0.42)
      }
    }

    // Bottom border
    ctx.strokeStyle = RULER_BORDER
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, canvasHeight - 0.5)
    ctx.lineTo(canvasWidth, canvasHeight - 0.5)
    ctx.stroke()
  }

  function drawVRuler(ctx: CanvasRenderingContext2D, canvasWidth: number, canvasHeight: number, panOffsetY = 0) {
    const dpr = window.devicePixelRatio || 1
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, canvasWidth, canvasHeight)
    ctx.fillStyle = RULER_BG
    ctx.fillRect(0, 0, canvasWidth, canvasHeight)

    const { scale } = viewport.value
    const offsetY = viewport.value.offsetY + panOffsetY
    const cellPx = CELL_PX * scale
    const step = labelStep.value

    const firstRow = Math.max(1, Math.floor(-offsetY / cellPx) + 1)
    const lastRow = Math.ceil((canvasHeight - offsetY) / cellPx) + 1

    ctx.font = RULER_FONT
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    for (let row = firstRow; row <= lastRow; row++) {
      const y = (row - 1) * cellPx + offsetY
      if (y < -cellPx || y > canvasHeight + cellPx) continue

      const isMajor = (row - 1) % 4 === 0
      const tickW = isMajor ? 7 : 3

      // Tick
      ctx.strokeStyle = RULER_TICK
      ctx.lineWidth = isMajor ? 1 : 0.5
      ctx.beginPath()
      ctx.moveTo(canvasWidth - tickW, y)
      ctx.lineTo(canvasWidth, y)
      ctx.stroke()

      // Label
      if ((row - 1) % step === 0) {
        ctx.fillStyle = RULER_LABEL
        ctx.fillText(String(row), canvasWidth * 0.45, y + cellPx * 0.5)
      }
    }

    // Right border
    ctx.strokeStyle = RULER_BORDER
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(canvasWidth - 0.5, 0)
    ctx.lineTo(canvasWidth - 0.5, canvasHeight)
    ctx.stroke()
  }

  // --- Grid lines (Konva sceneFunc) ---

  const gridLinesSceneFunc = computed(() => {
    if (!showGridLines.value) return null

    const bounds = visibleBounds.value
    const scale = viewport.value.scale

    return (context: any, shape: any) => {
      const ctx = context._context as CanvasRenderingContext2D

      const colMin = Math.max(0, Math.floor(bounds.left / CELL_PX))
      const colMax = Math.ceil(bounds.right / CELL_PX)
      const rowMin = Math.max(0, Math.floor(bounds.top / CELL_PX))
      const rowMax = Math.ceil(bounds.bottom / CELL_PX)

      // Minor grid lines (every cell)
      ctx.beginPath()
      ctx.strokeStyle = GRID_MINOR_STROKE
      ctx.lineWidth = 0.5 / scale
      for (let c = colMin; c <= colMax; c++) {
        if (c % 4 === 0) continue // skip major lines
        const x = c * CELL_PX
        ctx.moveTo(x, bounds.top)
        ctx.lineTo(x, bounds.bottom)
      }
      for (let r = rowMin; r <= rowMax; r++) {
        if (r % 4 === 0) continue
        const y = r * CELL_PX
        ctx.moveTo(bounds.left, y)
        ctx.lineTo(bounds.right, y)
      }
      ctx.stroke()

      // Major grid lines (every 4 cells = 1 inch)
      ctx.beginPath()
      ctx.strokeStyle = GRID_MAJOR_STROKE
      ctx.lineWidth = 1 / scale
      for (let c = colMin; c <= colMax; c++) {
        if (c % 4 !== 0) continue
        const x = c * CELL_PX
        ctx.moveTo(x, bounds.top)
        ctx.lineTo(x, bounds.bottom)
      }
      for (let r = rowMin; r <= rowMax; r++) {
        if (r % 4 !== 0) continue
        const y = r * CELL_PX
        ctx.moveTo(bounds.left, y)
        ctx.lineTo(bounds.right, y)
      }
      ctx.stroke()

      context.fillStrokeShape(shape)
    }
  })

  const gridLinesConfig = computed(() => {
    if (!gridLinesSceneFunc.value) return null
    return {
      sceneFunc: gridLinesSceneFunc.value,
      listening: false,
    }
  })

  // Stage size adjusted for rulers
  const adjustedStageSize = computed(() => {
    const { width, height } = stageSize.value
    if (!showRulers.value) return { width, height }
    return {
      width: Math.max(0, width - RULER_V_WIDTH),
      height: Math.max(0, height - RULER_H_HEIGHT),
    }
  })

  return {
    labelStep,
    visibleBounds,
    drawHRuler,
    drawVRuler,
    gridLinesConfig,
    adjustedStageSize,
  }
}
