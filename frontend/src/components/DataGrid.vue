<template>
  <div class="grid">
    <div class="grid-header">
      <h3>{{ title }}</h3>
      <button type="button" class="add" @click="addRow">+ Thêm</button>
    </div>
    <div class="grid-body">
      <table>
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key" :style="columnStyle(column)">
              {{ column.label }}
            </th>
            <th class="actions">Xóa</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in rows" :key="row.id ?? rowIndex">
            <td v-for="column in columns" :key="column.key">
              <span v-if="column.readonly">{{ row[column.key] }}</span>
              <select
                v-else-if="column.type === 'select'"
                :value="row[column.key]"
                @change="updateCell(rowIndex, column.key, ($event.target as HTMLSelectElement).value, column)"
              >
                <option v-for="option in column.options" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
              <input
                v-else
                :type="column.type === 'number' ? 'number' : 'text'"
                :value="row[column.key]"
                @input="updateCell(rowIndex, column.key, ($event.target as HTMLInputElement).value, column)"
              />
            </td>
            <td class="actions">
              <button type="button" class="ghost" @click="removeRow(rowIndex)">Xóa</button>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td :colspan="columns.length + 1" class="empty">
              Chưa có dữ liệu
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
export type ColumnDef = {
  key: string
  label: string
  type?: 'text' | 'number' | 'select'
  options?: Array<{ value: string; label: string }>
  readonly?: boolean
  width?: string
}

const props = defineProps<{
  title: string
  columns: ColumnDef[]
  rows: Array<Record<string, any>>
  defaultRow: Record<string, any>
}>()

const emit = defineEmits<{
  (event: 'update:rows', value: Array<Record<string, any>>): void
  (event: 'row:add', row: Record<string, any>): void
  (event: 'row:remove', row: Record<string, any>): void
  (event: 'row:change', payload: { row: Record<string, any>; key: string; value: any; index: number }): void
}>()

function updateCell(index: number, key: string, value: string, column: ColumnDef) {
  const parsed = column.type === 'number' ? Number(value) : value
  const next = props.rows.map((row, rowIndex) => {
    if (rowIndex !== index) return row
    return { ...row, [key]: parsed }
  })
  emit('row:change', { row: next[index], key, value: parsed, index })
  emit('update:rows', next)
}

function addRow() {
  const fallbackId = typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `row-${Date.now()}`
  const row = { id: fallbackId, ...props.defaultRow }
  emit('update:rows', [...props.rows, row])
  emit('row:add', row)
}

function removeRow(index: number) {
  const removed = props.rows[index]
  if (removed) {
    emit('row:remove', removed)
  }
  const next = props.rows.filter((_, rowIndex) => rowIndex !== index)
  emit('update:rows', next)
}

function columnStyle(column: ColumnDef) {
  return column.width ? { width: column.width } : undefined
}
</script>

<style scoped>
.grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.grid-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.grid-header h3 {
  margin: 0;
  font-size: 16px;
}

.grid-header .add {
  border: none;
  border-radius: 10px;
  padding: 6px 12px;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
}

.grid-body {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(28, 28, 28, 0.08);
}

th {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
}

input,
select {
  width: 100%;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid rgba(28, 28, 28, 0.12);
  font-family: inherit;
  font-size: 13px;
}

.actions {
  width: 64px;
}

.ghost {
  border: 1px solid rgba(28, 28, 28, 0.18);
  background: transparent;
  border-radius: 8px;
  padding: 4px 8px;
  cursor: pointer;
}

.empty {
  text-align: center;
  color: var(--muted);
  padding: 12px;
}
</style>
