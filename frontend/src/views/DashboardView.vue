<template>
  <div class="space-y-6">
    <!-- Filters -->
    <div class="card p-3 grid grid-cols-2 md:grid-cols-6 gap-2 items-end">
      <div>
        <label class="label">Robot</label>
        <select class="select" v-model="filters.robot_id" @change="reload">
          <option :value="null">All</option>
          <option v-for="r in robots" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
      <div>
        <label class="label">Group</label>
        <select class="select" v-model="filters.group_id" @change="reload">
          <option :value="null">All</option>
          <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
      </div>
      <div>
        <label class="label">Strategy</label>
        <select class="select" v-model="filters.strategy_id" @change="reload">
          <option :value="null">All</option>
          <option v-for="s in strategies" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div>
        <label class="label">Host</label>
        <input class="input" v-model="filters.target_host" placeholder="example.com" @change="reload" />
      </div>
      <div>
        <label class="label">Range</label>
        <select class="select" v-model="rangeKey" @change="onRangeChange">
          <option value="1h">Last hour</option>
          <option value="6h">Last 6 hours</option>
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
        </select>
      </div>
      <div>
        <label class="label">Bucket</label>
        <select class="select" v-model="interval" @change="reload">
          <option value="minute">minute</option>
          <option value="hour">hour</option>
          <option value="day">day</option>
        </select>
      </div>
    </div>

    <!-- KPI cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <KpiCard label="Total requests" :value="summary.total_requests" />
      <KpiCard label="Success rate"
               :value="(summary.success_rate * 100).toFixed(1) + '%'"
               :tone="summary.success_rate >= 0.9 ? 'success' : summary.success_rate >= 0.7 ? 'warn' : 'danger'" />
      <KpiCard label="Avg latency" :value="summary.average_duration_ms.toFixed(0) + ' ms'" />
      <KpiCard label="Active proxies / robots"
               :value="`${summary.active_proxies} / ${summary.active_robots}`" />
    </div>

    <!-- Timeseries -->
    <div class="card p-4">
      <h2 class="font-medium text-ink-700 mb-3">Requests &amp; success rate over time</h2>
      <div class="h-64">
        <LineChart v-if="timeseries.length" :data="timeseriesData" :options="timeseriesOptions" />
        <div v-else class="text-sm text-ink-400 text-center py-12">No data for this range.</div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Status code distribution -->
      <div class="card p-4">
        <h2 class="font-medium text-ink-700 mb-3">Status code distribution</h2>
        <div class="h-64">
          <BarChart v-if="statusCodes.length" :data="statusCodesData" :options="barOptions" />
          <div v-else class="text-sm text-ink-400 text-center py-12">No data.</div>
        </div>
      </div>
      <!-- Success vs failure -->
      <div class="card p-4">
        <h2 class="font-medium text-ink-700 mb-3">Outcome split</h2>
        <div class="h-64">
          <DoughnutChart :data="outcomeData" :options="doughnutOptions" />
        </div>
      </div>
    </div>

    <!-- Comparison -->
    <ComparisonCard :params="params" />

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <TopList title="Top robots" :items="topRobots" />
      <TopList title="Top proxies" :items="topProxies" />
      <TopList title="Top hosts" :items="topHosts" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { api } from '@/api';
import LineChart from '@/components/charts/LineChart.vue';
import BarChart from '@/components/charts/BarChart.vue';
import DoughnutChart from '@/components/charts/DoughnutChart.vue';
import KpiCard from '@/components/ui/KpiCard.vue';
import TopList from '@/components/ui/TopList.vue';
import ComparisonCard from '@/components/charts/ComparisonCard.vue';
import type { MetricsSummary, ProxyGroup, Robot, StatusCodeBucket, StrategyConfig, TimeseriesPoint, TopItem } from '@/api/types';

const robots = ref<Robot[]>([]);
const groups = ref<ProxyGroup[]>([]);
const strategies = ref<StrategyConfig[]>([]);

const filters = ref<{ robot_id: number | null; group_id: number | null; strategy_id: number | null; target_host: string }>({
  robot_id: null, group_id: null, strategy_id: null, target_host: '',
});
const rangeKey = ref('24h');
const interval = ref<'minute' | 'hour' | 'day'>('hour');
const since = ref<string>(new Date(Date.now() - 24 * 3600 * 1000).toISOString());

const summary = ref<MetricsSummary>({
  total_requests: 0, successful_requests: 0, failed_requests: 0,
  success_rate: 0, average_duration_ms: 0, active_proxies: 0, active_robots: 0,
});
const timeseries = ref<TimeseriesPoint[]>([]);
const statusCodes = ref<StatusCodeBucket[]>([]);
const topRobots = ref<TopItem[]>([]);
const topProxies = ref<TopItem[]>([]);
const topHosts = ref<TopItem[]>([]);

const onRangeChange = () => {
  const map: Record<string, number> = { '1h': 1, '6h': 6, '24h': 24, '7d': 24 * 7, '30d': 24 * 30 };
  const hours = map[rangeKey.value] ?? 24;
  since.value = new Date(Date.now() - hours * 3600 * 1000).toISOString();
  interval.value = hours <= 6 ? 'minute' : hours <= 24 * 2 ? 'hour' : 'day';
  reload();
};

const params = computed(() => ({
  robot_id: filters.value.robot_id ?? undefined,
  group_id: filters.value.group_id ?? undefined,
  strategy_id: filters.value.strategy_id ?? undefined,
  target_host: filters.value.target_host || undefined,
  since: since.value,
}));

const reload = async () => {
  const p = params.value;
  [summary.value, timeseries.value, statusCodes.value, topRobots.value, topProxies.value, topHosts.value] = await Promise.all([
    api.metricsSummary(p),
    api.metricsTimeseries({ ...p, interval: interval.value }),
    api.metricsStatusCodes(p),
    api.topRobots({ ...p, limit: 8 }),
    api.topProxies({ ...p, limit: 8 }),
    api.topHosts({ ...p, limit: 8 }),
  ]);
};

const timeseriesData = computed(() => ({
  labels: timeseries.value.map((p) => new Date(p.bucket).toLocaleString()),
  datasets: [
    {
      label: 'Successes',
      data: timeseries.value.map((p) => p.success),
      backgroundColor: 'rgba(44,108,255,.15)',
      borderColor: '#2c6cff',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      yAxisID: 'y',
    },
    {
      label: 'Failures',
      data: timeseries.value.map((p) => p.failure),
      backgroundColor: 'rgba(239,68,68,.15)',
      borderColor: '#ef4444',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      yAxisID: 'y',
    },
    {
      label: 'Success rate',
      data: timeseries.value.map((p) => p.success_rate * 100),
      borderColor: '#10b981',
      borderDash: [4, 4],
      borderWidth: 2,
      fill: false,
      tension: 0.2,
      yAxisID: 'y1',
      pointRadius: 0,
    },
  ],
}));

const timeseriesOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  scales: {
    y: { beginAtZero: true, title: { display: true, text: 'Requests' } },
    y1: { beginAtZero: true, max: 100, position: 'right', grid: { drawOnChartArea: false }, ticks: { callback: (v: any) => `${v}%` } },
  },
  plugins: { legend: { position: 'bottom' } },
};

const statusCodesData = computed(() => ({
  labels: statusCodes.value.map((s) => s.status_code?.toString() ?? '—'),
  datasets: [{
    label: 'Requests',
    data: statusCodes.value.map((s) => s.count),
    backgroundColor: statusCodes.value.map((s) => {
      const c = s.status_code ?? 0;
      if (c >= 500) return '#ef4444';
      if (c >= 400) return '#f59e0b';
      if (c >= 300) return '#3b82f6';
      if (c >= 200) return '#10b981';
      return '#94a3b8';
    }),
  }],
}));

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
};

const outcomeData = computed(() => ({
  labels: ['Successes', 'Failures'],
  datasets: [{
    data: [summary.value.successful_requests, summary.value.failed_requests],
    backgroundColor: ['#10b981', '#ef4444'],
    borderWidth: 0,
  }],
}));

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '65%',
  plugins: { legend: { position: 'bottom' } },
};

onMounted(async () => {
  [robots.value, groups.value, strategies.value] = await Promise.all([
    api.listRobots(),
    api.listGroups(),
    api.listStrategyConfigs(),
  ]);
  await reload();
});
</script>
