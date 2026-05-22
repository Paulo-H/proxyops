<template>
  <div class="card p-4">
    <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
      <h2 class="font-medium text-ink-700">Comparison</h2>
      <div class="flex items-center gap-2">
        <label class="text-xs text-ink-500">by</label>
        <select class="select max-w-[10rem] py-1" v-model="dimension" @change="reload">
          <option value="strategy">Strategy</option>
          <option value="robot">Robot</option>
          <option value="provider">Provider</option>
          <option value="group">Group</option>
          <option value="host">Host</option>
          <option value="proxy">Proxy</option>
        </select>
        <select class="select max-w-[9rem] py-1" v-model="metric">
          <option value="success_rate">Success rate</option>
          <option value="total">Volume</option>
          <option value="avg_duration_ms">Avg latency</option>
        </select>
      </div>
    </div>

    <div v-if="rows.length === 0" class="text-sm text-ink-400 text-center py-10">
      No data for this dimension / range.
    </div>

    <template v-else>
      <div class="h-64 mb-4">
        <BarChart :data="chartData" :options="chartOptions" />
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full">
          <thead class="bg-ink-50">
            <tr>
              <th class="th">{{ dimensionLabel }}</th>
              <th class="th text-right">Requests</th>
              <th class="th text-right">Success</th>
              <th class="th text-right">Success rate</th>
              <th class="th text-right">Avg latency</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.key" class="hover:bg-ink-50/60">
              <td class="td font-medium">{{ r.label ?? r.key }}</td>
              <td class="td text-right tabular-nums">{{ r.total }}</td>
              <td class="td text-right tabular-nums">{{ r.success }}</td>
              <td class="td text-right tabular-nums">
                <span :class="rateClass(r.success_rate)">{{ (r.success_rate * 100).toFixed(1) }}%</span>
              </td>
              <td class="td text-right tabular-nums">{{ r.avg_duration_ms.toFixed(0) }} ms</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { api } from '@/api';
import BarChart from '@/components/charts/BarChart.vue';
import type { MetricsFilters, TopItem } from '@/api/types';

const props = defineProps<{ params: MetricsFilters }>();

const dimension = ref<string>('strategy');
const metric = ref<'success_rate' | 'total' | 'avg_duration_ms'>('success_rate');
const rows = ref<TopItem[]>([]);

const dimensionLabel = computed(() => ({
  strategy: 'Strategy', robot: 'Robot', provider: 'Provider',
  group: 'Group', host: 'Host', proxy: 'Proxy',
}[dimension.value] ?? 'Item'));

const reload = async () => {
  rows.value = await api.metricsBreakdown({ ...props.params, dimension: dimension.value, limit: 20 });
};

// Refetch whenever the dashboard filters change.
watch(() => props.params, reload, { deep: true });

const metricMeta = computed(() => ({
  success_rate: { label: 'Success rate (%)', color: '#10b981', scale: (v: number) => v * 100 },
  total:        { label: 'Requests',         color: '#2c6cff', scale: (v: number) => v },
  avg_duration_ms: { label: 'Avg latency (ms)', color: '#f59e0b', scale: (v: number) => v },
}[metric.value]));

const chartData = computed(() => ({
  labels: rows.value.map((r) => r.label ?? r.key),
  datasets: [{
    label: metricMeta.value.label,
    data: rows.value.map((r) => metricMeta.value.scale((r as any)[metric.value])),
    backgroundColor: metricMeta.value.color,
    borderRadius: 4,
  }],
}));

const chartOptions = computed(() => ({
  indexAxis: 'y' as const,
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: {
      beginAtZero: true,
      max: metric.value === 'success_rate' ? 100 : undefined,
      ticks: metric.value === 'success_rate' ? { callback: (v: any) => `${v}%` } : {},
    },
  },
}));

const rateClass = (rate: number) =>
  rate >= 0.9 ? 'text-emerald-600' : rate >= 0.7 ? 'text-amber-600' : 'text-red-600';

onMounted(reload);
</script>
