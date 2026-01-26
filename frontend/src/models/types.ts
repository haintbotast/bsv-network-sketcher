export type Point = {
  x: number
  y: number
}

export type Size = {
  width: number
  height: number
}

export type Viewport = {
  scale: number
  offsetX: number
  offsetY: number
}

export type AreaModel = {
  id: string
  name: string
  x: number
  y: number
  width: number
  height: number
  fill: string
  stroke: string
}

export type DeviceModel = {
  id: string
  areaId: string
  name: string
  x: number
  y: number
  width: number
  height: number
  type: string
}

export type LinkModel = {
  id: string
  fromDeviceId: string
  toDeviceId: string
  fromPort: string
  toPort: string
  style: 'solid' | 'dashed' | 'dotted'
}
