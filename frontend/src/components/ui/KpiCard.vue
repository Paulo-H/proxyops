<template>
  <div class="card p-4">
    <div class="text-xs uppercase tracking-wider text-ink-500">{{ label }}</div>
    <div class="mt-1 text-2xl font-semibold tabular-nums" :class="toneClass">
      {{ value }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  label: string;
  value: string | number;
  tone?: 'default' | 'success' | 'warn' | 'danger';
}>(), { tone: 'default' });

const toneClass = computed(() => ({
  default: 'text-ink-800',
  success: 'text-emerald-600',
  warn: 'text-amber-600',
  danger: 'text-red-600',
}[props.tone]));
</script>
