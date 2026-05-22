<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold text-ink-800">Request log</h1>

    <div class="card p-3 grid grid-cols-2 md:grid-cols-7 gap-2">
      <select class="select" v-model="filters.robot_id" @change="reload">
        <option :value="null">All robots</option>
        <option v-for="r in robots" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
      <select class="select" v-model="filters.group_id" @change="reload">
        <option :value="null">All groups</option>
        <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
      </select>
      <select class="select" v-model="filters.strategy_id" @change="reload">
        <option :value="null">All strategies</option>
        <option v-for="s in strategies" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <input class="input" v-model="filters.target_host" placeholder="host (e.g. example.com)" @change="reload" />
      <select class="select" v-model="filters.success" @change="reload">
        <option :value="null">Any outcome</option>
        <option :value="true">Successes</option>
        <option :value="false">Failures</option>
      </select>
      <input class="input" type="number" min="100" max="599" placeholder="status ≥" v-model.number="filters.status_code_min" @change="reload" />
      <input class="input" type="number" min="100" max="599" placeholder="status ≤" v-model.number="filters.status_code_max" @change="reload" />
    </div>

    <DataTable
      :rows="rows"
      :columns="[
        { key: 'created_at', label: 'When' },
        { key: 'robot_name', label: 'Robot' },
        { key: 'target_host', label: 'Host' },
        { key: 'strategy_kind', label: 'Strategy' },
        { key: 'proxy_id', label: 'Proxy' },
        { key: 'status_code', label: 'Status' },
        { key: 'duration_ms', label: 'Duration' },
        { key: 'success', label: 'Result' },
      ]"
      :row-key="(r) => r.id"
      emptyText="No matching requests."
    >
      <template #cell-created_at="{ row }">
        <span class="text-xs text-ink-600 tabular-nums">{{ formatDate(row.created_at) }}</span>
      </template>
      <template #cell-target_host="{ row }">
        <span class="font-mono text-xs">{{ row.target_host ?? '—' }}</span>
      </template>
      <template #cell-strategy_kind="{ row }">
        <span v-if="row.strategy_kind" class="badge-info">{{ row.strategy_kind }}</span>
        <span v-else class="text-ink-400">—</span>
      </template>
      <template #cell-proxy_id="{ row }">
        <span class="font-mono text-xs">#{{ row.proxy_id }}</span>
      </template>
      <template #cell-status_code="{ row }">
        <span :class="statusClass(row.status_code)">{{ row.status_code ?? '—' }}</span>
      </template>
      <template #cell-duration_ms="{ row }">
        <span v-if="row.duration_ms != null" class="tabular-nums">{{ row.duration_ms.toFixed(0) }} ms</span>
        <span v-else class="text-ink-400">—</span>
      </template>
      <template #cell-success="{ row }">
        <span v-if="row.success" class="badge-success">OK</span>
        <span v-else class="badge-danger">Fail</span>
      </template>
    </DataTable>

    <div class="flex justify-center">
      <button class="btn-secondary" @click="loadMore" v-if="canLoadMore">Load more</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '@/api';
import DataTable from '@/components/ui/DataTable.vue';
import type { RequestLog, Robot, ProxyGroup, StrategyConfig } from '@/api/types';

const rows = ref<RequestLog[]>([]);
const robots = ref<Robot[]>([]);
const groups = ref<ProxyGroup[]>([]);
const strategies = ref<StrategyConfig[]>([]);
const filters = ref<any>({
  robot_id: null, group_id: null, strategy_id: null, target_host: '',
  success: null, status_code_min: null, status_code_max: null,
});
const offset = ref(0);
const limit = 200;
const canLoadMore = ref(false);

const reload = async () => {
  offset.value = 0;
  rows.value = await fetchPage();
  canLoadMore.value = rows.value.length === limit;
};

const fetchPage = async () => {
  return api.listLogs({
    robot_id: filters.value.robot_id ?? undefined,
    group_id: filters.value.group_id ?? undefined,
    strategy_id: filters.value.strategy_id ?? undefined,
    target_host: filters.value.target_host || undefined,
    success: filters.value.success === null ? undefined : filters.value.success,
    status_code_min: filters.value.status_code_min || undefined,
    status_code_max: filters.value.status_code_max || undefined,
    limit, offset: offset.value,
  });
};

const loadMore = async () => {
  offset.value += limit;
  const next = await fetchPage();
  rows.value.push(...next);
  canLoadMore.value = next.length === limit;
};

const formatDate = (iso: string) => new Date(iso).toLocaleString();
const statusClass = (code: number | null) => {
  if (code == null) return 'badge-muted';
  if (code >= 500) return 'badge-danger';
  if (code >= 400) return 'badge-warn';
  if (code >= 300) return 'badge-info';
  return 'badge-success';
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
