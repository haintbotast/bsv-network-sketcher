const CELL_RE = /^\s*([A-Za-z]+)\s*([1-9]\d*)\s*$/
const RANGE_RE = /^\s*([A-Za-z]+[1-9]\d*)\s*(?::\s*([A-Za-z]+[1-9]\d*)\s*)?$/

export const GRID_CELL_UNITS = 0.25

function colLettersToIndex(letters: string): number {
  let value = 0
  for (const ch of letters.toUpperCase()) {
    if (ch < 'A' || ch > 'Z') throw new Error(`Cột '${letters}' không hợp lệ`)
    value = value * 26 + (ch.charCodeAt(0) - 64)
  }
  return value
}

export function colIndexToLetters(index: number): string {
  if (index < 1) throw new Error('Chỉ số cột phải >= 1')
  let n = index
  let out = ''
  while (n > 0) {
    n -= 1
    out = String.fromCharCode(65 + (n % 26)) + out
    n = Math.floor(n / 26)
  }
  return out
}

export function parseExcelCell(cell: string): { col: number; row: number } {
  const match = CELL_RE.exec(cell || '')
  if (!match) throw new Error(`Ô '${cell}' không hợp lệ (vd: A1)`) 
  return {
    col: colLettersToIndex(match[1]),
    row: Number(match[2])
  }
}

export function formatExcelCell(col: number, row: number): string {
  if (row < 1) throw new Error('Dòng phải >= 1')
  return `${colIndexToLetters(col)}${row}`
}

export function normalizeExcelRange(gridRange: string): string {
  const match = RANGE_RE.exec(gridRange || '')
  if (!match) throw new Error('Grid range không hợp lệ (vd: A1 hoặc A1:B3)')
  const left = match[1]
  const right = match[2] || left

  const start = parseExcelCell(left)
  const end = parseExcelCell(right)

  const colStart = Math.min(start.col, end.col)
  const colEnd = Math.max(start.col, end.col)
  const rowStart = Math.min(start.row, end.row)
  const rowEnd = Math.max(start.row, end.row)

  const first = formatExcelCell(colStart, rowStart)
  const last = formatExcelCell(colEnd, rowEnd)
  return first === last ? first : `${first}:${last}`
}

export function parseExcelRange(gridRange: string) {
  const normalized = normalizeExcelRange(gridRange)
  const parts = normalized.split(':')
  const left = parseExcelCell(parts[0])
  const right = parseExcelCell(parts[1] || parts[0])
  return {
    colStart: left.col,
    rowStart: left.row,
    colEnd: right.col,
    rowEnd: right.row,
  }
}

export function excelRangeToRectUnits(gridRange: string, cellUnits = GRID_CELL_UNITS) {
  const parsed = parseExcelRange(gridRange)
  return {
    x: (parsed.colStart - 1) * cellUnits,
    y: (parsed.rowStart - 1) * cellUnits,
    width: (parsed.colEnd - parsed.colStart + 1) * cellUnits,
    height: (parsed.rowEnd - parsed.rowStart + 1) * cellUnits,
    ...parsed,
  }
}

export function rectUnitsToExcelRange(
  x: number,
  y: number,
  width: number,
  height: number,
  cellUnits = GRID_CELL_UNITS,
): string {
  const safeW = Math.max(cellUnits, width)
  const safeH = Math.max(cellUnits, height)
  const colStart = Math.max(1, Math.floor(x / cellUnits + 1e-9) + 1)
  const rowStart = Math.max(1, Math.floor(y / cellUnits + 1e-9) + 1)
  const colSpan = Math.max(1, Math.round(safeW / cellUnits))
  const rowSpan = Math.max(1, Math.round(safeH / cellUnits))
  const colEnd = colStart + colSpan - 1
  const rowEnd = rowStart + rowSpan - 1
  const start = formatExcelCell(colStart, rowStart)
  const end = formatExcelCell(colEnd, rowEnd)
  return start === end ? start : `${start}:${end}`
}
