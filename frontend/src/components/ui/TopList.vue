<template>
  <div class="card p-4">
    <h2 class="font-medium text-ink-700 mb-3">{{ title }}</h2>
    <div v-if="items.length === 0" class="text-sm text-ink-400 text-center py-8">No data.</div>
    <ul v-else class="space-y-2">
      <li v-for="item in items" :key="item.key" class="flex items-center gap-3 text-sm">
        <div class="flex-1 truncate">
          <div class="truncate font-medium text-ink-700">{{ item.label ?? item.key }}</div>
          <div class="text-xs text-ink-500 tabular-nums">{{ item.total }} requests · {{ (item.success_rate * 100).toFixed(0) }}% ok</div>
        </div>
        <div class="w-20 h-1.5 rounded-full bg-ink-100 overflow-hidden">
          <div class="h-full bg-brand-500" :style="`width:${Math.round(item.success_rate * 100)}%`" />
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { TopItem } from '@/api/types';
defineProps<{ title: string; items: TopItem[] }>();
</script>
