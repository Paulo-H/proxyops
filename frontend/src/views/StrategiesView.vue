<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-ink-800">Rotation strategies</h1>
      <button class="btn-primary" @click="openCreate" :disabled="!auth.canEdit">+ New preset</button>
    </div>

    <p class="text-sm text-ink-600 max-w-3xl">
      Strategy presets are named, parameterized rotation algorithms. A group binds
      to one preset, and a robot can override it on a per-request basis via
      <code class="font-mono text-xs">strategy_id</code> in <code class="font-mono text-xs">/rotation/acquire</code>.
    </p>

    <DataTable
      :rows="rows"
      :columns="[
        { key: 'name', label: 'Name' },
        { key: 'kind', label: 'Algorithm' },
        { key: 'description', label: 'Description' },
        { key: 'params', label: 'Parameters' },
      ]"
      :row-key="(r) => r.id"
      emptyText="No strategy presets yet."
    >
      <template #cell-kind="{ row }">
        <span class="badge-info">{{ kindLabel(row.kind) }}</span>
      </template>
      <template #cell-params="{ row }">
        <code class="text-xs font-mono text-ink-600">
          {{ Object.keys(row.parameters).length }} param{{ Object.keys(row.parameters).length === 1 ? '' : 's' }}
        </code>
      </template>
      <template #actions="{ row }">
        <button class="btn-ghost text-sm" @click="openEdit(row)" :disabled="!auth.canEdit">Edit</button>
        <button class="btn-ghost text-sm text-red-600" @click="onDelete(row)" :disabled="!auth.canEdit">Delete</button>
      </template>
    </DataTable>

    <Modal v-model="formOpen" :title="editing ? 'Edit preset' : 'New preset'">
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
          <label class="label">Algorithm</label>
          <select class="select" v-model="form.kind" :disabled="!!editing" @change="resetParameters">
            <option v-for="k in kinds" :key="k.kind" :value="k.kind">{{ k.label }}</option>
          </select>
          <p class="text-xs text-ink-500 mt-1">{{ currentKindInfo?.description }}</p>
        </div>

        <div v-if="currentKindInfo && currentKindInfo.parameters.length" class="space-y-2">
          <h3 class="text-sm font-medium text-ink-700">Parameters</h3>
          <div v-for="p in currentKindInfo.parameters" :key="p.name" class="grid grid-cols-3 gap-2 items-start">
            <div class="col-span-1">
              <div class="text-sm font-mono">{{ p.name }}</div>
              <div class="text-xs text-ink-500">{{ p.description }}</div>
            </div>
            <input
              class="input col-span-2"
              :type="p.type === 'int' || p.type === 'float' ? 'number' : 'text'"
              :step="p.type === 'float' ? '0.0001' : '1'"
              :min="p.min ?? undefined"
              :max="p.max ?? undefined"
              v-model.number="form.parameters[p.name]"
            />
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
import { computed, onMounted, ref } from 'vue';
import { api } from '@/api';
import { useAuthStore } from '@/stores/auth';
import DataTable from '@/components/ui/DataTable.vue';
import Modal from '@/components/ui/Modal.vue';
import type { StrategyConfig, StrategyKind, StrategyKindInfo } from '@/api/types';

const auth = useAuthStore();
const rows = ref<StrategyConfig[]>([]);
const kinds = ref<StrategyKindInfo[]>([]);

const formOpen = ref(false);
const editing = ref<StrategyConfig | null>(null);
const saving = ref(false);
const error = ref('');

const form = ref<{ name: string; description: string; kind: StrategyKind; parameters: Record<string, any> }>({
  name: '',
  description: '',
  kind: 'round_robin',
  parameters: {},
});

const currentKindInfo = computed(() => kinds.value.find((k) => k.kind === form.value.kind));

const resetParameters = () => {
  const info = currentKindInfo.value;
  form.value.parameters = {};
  if (info) {
    for (const p of info.parameters) form.value.parameters[p.name] = p.default;
  }
};

const reload = async () => { rows.value = await api.listStrategyConfigs(); };

const kindLabel = (k: StrategyKind) => kinds.value.find((kk) => kk.kind === k)?.label ?? k;

const openCreate = () => {
  editing.value = null;
  form.value = { name: '', description: '', kind: 'round_robin', parameters: {} };
  resetParameters();
  formOpen.value = true;
};

const openEdit = (row: StrategyConfig) => {
  editing.value = row;
  form.value = {
    name: row.name,
    description: row.description ?? '',
    kind: row.kind,
    parameters: { ...row.parameters },
  };
  formOpen.value = true;
};

const submit = async () => {
  saving.value = true; error.value = '';
  try {
    const payload: any = {
      name: form.value.name,
      description: form.value.description || null,
      parameters: form.value.parameters,
    };
    if (!editing.value) payload.kind = form.value.kind;
    if (editing.value) await api.updateStrategyConfig(editing.value.id, payload);
    else await api.createStrategyConfig(payload);
    formOpen.value = false;
    await reload();
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? 'Failed to save.';
  } finally {
    saving.value = false;
  }
};

const onDelete = async (row: StrategyConfig) => {
  if (!confirm(`Delete strategy "${row.name}"?`)) return;
  await api.deleteStrategyConfig(row.id);
  await reload();
};

onMounted(async () => {
  kinds.value = await api.listStrategyKinds();
  await reload();
});
</script>
