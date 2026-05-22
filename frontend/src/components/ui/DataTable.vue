<template>
  <div class="card overflow-hidden">
    <div v-if="$slots.toolbar" class="px-4 py-3 border-b border-ink-100 flex items-center gap-2 flex-wrap">
      <slot name="toolbar" />
    </div>
    <div class="overflow-x-auto">
      <table class="min-w-full">
        <thead class="bg-ink-50">
          <tr>
            <th v-for="c in columns" :key="c.key" class="th" :style="c.width ? `width:${c.width}` : ''">
              {{ c.label }}
            </th>
            <th v-if="$slots.actions" class="th w-1">&nbsp;</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0">
            <td :colspan="columns.length + ($slots.actions ? 1 : 0)" class="td text-center text-ink-500 py-10">
              {{ emptyText }}
            </td>
          </tr>
          <tr v-for="row in rows" :key="rowKey(row)" class="hover:bg-ink-50/60 transition">
            <td v-for="c in columns" :key="c.key" class="td">
              <slot :name="`cell-${c.key}`" :row="row">{{ readKey(row, c.key) }}</slot>
            </td>
            <td v-if="$slots.actions" class="td text-right whitespace-nowrap">
              <slot name="actions" :row="row" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts" generic="T extends Record<string, any>">
defineProps<{
  rows: T[];
  columns: { key: string; label: string; width?: string }[];
  rowKey: (row: T) => string | number;
  emptyText?: string;
}>();

const readKey = (row: any, key: string): any => {
  return key.split('.').reduce((acc, k) => (acc == null ? acc : acc[k]), row);
};
</script>
