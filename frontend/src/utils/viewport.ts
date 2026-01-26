import type { Viewport } from '../models/types'

export function logicalToView(value: number, scale: number, offset: number) {
  return value * scale + offset
}

export function viewToLogical(value: number, scale: number, offset: number) {
  return (value - offset) / scale
}

export function logicalRectToView(rect: { x: number; y: number; width: number; height: number }, viewport: Viewport) {
  return {
    x: logicalToView(rect.x, viewport.scale, viewport.offsetX),
    y: logicalToView(rect.y, viewport.scale, viewport.offsetY),
    width: rect.width * viewport.scale,
    height: rect.height * viewport.scale
  }
}

export function getVisibleBounds(stage: { width: number; height: number }, viewport: Viewport) {
  const left = viewToLogical(0, viewport.scale, viewport.offsetX)
  const top = viewToLogical(0, viewport.scale, viewport.offsetY)
  const right = viewToLogical(stage.width, viewport.scale, viewport.offsetX)
  const bottom = viewToLogical(stage.height, viewport.scale, viewport.offsetY)
  return {
    left: Math.min(left, right),
    right: Math.max(left, right),
    top: Math.min(top, bottom),
    bottom: Math.max(top, bottom)
  }
}
