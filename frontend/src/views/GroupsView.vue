<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-ink-800">Proxy groups</h1>
      <button class="btn-primary" @click="openCreate" :disabled="!auth.canEdit">+ New group</button>
    </div>

    <DataTable
      :rows="rows"
      :columns="[
        { key: 'name', label: 'Name' },
        { key: 'description', label: 'Description' },
        { key: 'proxy_count', label: 'Proxies' },
        { key: 'robot_count', label: 'Robots' },
        { key: 'strategy', label: 'Default strategy' },
      ]"
      :row-key="(r) => r.id"
      emptyText="No groups yet."
    >
      <template #cell-strategy="{ row }">
        <span v-if="row.default_strategy_id" class="badge-info">
          {{ strategyName(row.default_strategy_id) }}
        </span>
        <span v-else class="text-ink-400">— round_robin —</span>
      </template>
      <template #actions="{ row }">
        <button class="btn-ghost text-sm" @click="openEdit(row)" :disabled="!auth.canEdit">Edit</button>
        <button class="btn-ghost text-sm text-red-600" @click="onDelete(row)" :disabled="!auth.canEdit">Delete</button>
      </template>
    </DataTable>

    <Modal v-model="formOpen" :title="editing ? 'Edit group' : 'New group'">
      <div class="space-y-3">
        <div>
          <label class="label">Name</label>
          <input class="input" v-model="form.name" />
        </div>
        <div>
          <label class="label">Description</label>
          <textarea class="textarea" rows="2" v-model="form.description" />
        </div>
        <div>
          <label class="label">Default strategy</label>
          <select class="select" v-model="form.default_strategy_id">
            <option :value="null">— None (use round-robin) —</option>
            <option v-for="s in strategies" :key="s.id" :value="s.id">
              {{ s.name }} ({{ s.kind }})
            </option>
          </select>
        </div>
        <div>
          <label class="label">Proxies in this group</label>
          <div class="border border-ink-200 rounded-lg max-h-48 overflow-y-auto p-2">
            <label v-for="p in proxies" :key="p.id" class="flex items-center gap-2 text-sm py-0.5">
              <input type="checkbox" :value="p.id" v-model="form.proxy_ids" />
              <span class="font-mono">{{ p.host }}:{{ p.port }}</span>
              <span class="text-ink-400">— {{ p.protocol }}</span>
            </label>
            <p v-if="proxies.length === 0" class="text-ink-400 text-sm">No proxies registered yet.</p>
          </div>
        </div>
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="formOpen = false">Cancel</button>
        <button class="btn-primary" @click="submit" :disabled="saving">Save</button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '@/api';
import { useAuthStore } from '@/stores/auth';
import DataTable from '@/components/ui/DataTable.vue';
import Modal from '@/components/ui/Modal.vue';
import type { ProxyGroup, Proxy, StrategyConfig } from '@/api/types';

const auth = useAuthStore();
const rows = ref<ProxyGroup[]>([]);
const proxies = ref<Proxy[]>([]);
const strategies = ref<StrategyConfig[]>([]);

const formOpen = ref(false);
const editing = ref<ProxyGroup | null>(null);
const saving = ref(false);
const error = ref('');

const emptyForm = () => ({
  name: '',
  description: '',
  default_strategy_id: null as number | null,
  proxy_ids: [] as number[],
});
const form = ref(emptyForm());

const reload = async () => { rows.value = await api.listGroups(); };

const openCreate = () => { editing.value = null; form.value = emptyForm(); formOpen.value = true; };
const openEdit = async (row: ProxyGroup) => {
  const allProxies = await api.listProxies({ group_id: row.id });
  editing.value = row;
  form.value = {
    name: row.name,
    description: row.description ?? '',
    default_strategy_id: row.default_strategy_id,
    proxy_ids: allProxies.map((p) => p.id),
  };
  formOpen.value = true;
};

const submit = async () => {
  saving.value = true;
  error.value = '';
  const payload: any = {
    name: form.value.name,
    description: form.value.description || null,
    default_strategy_id: form.value.default_strategy_id,
    proxy_ids: form.value.proxy_ids,
  };
  try {
    if (editing.value) await api.updateGroup(editing.value.id, payload);
    else await api.createGroup(payload);
    formOpen.value = false;
    await reload();
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? 'Failed to save.';
  } finally {
    saving.value = false;
  }
};

const onDelete = async (row: ProxyGroup) => {
  if (!confirm(`Delete group "${row.name}"?`)) return;
  await api.deleteGroup(row.id);
  await reload();
};

const strategyName = (id: number) => strategies.value.find((s) => s.id === id)?.name ?? `#${id}`;

onMounted(async () => {
  [proxies.value, strategies.value] = await Promise.all([
    api.listProxies(),
    api.listStrategyConfigs(),
  ]);
  await reload();
});
</script>
