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
        <span v-if="row.parameters && row.parameters.mode === 'simple'" class="badge-success">Simple</span>
        <code v-else class="text-xs font-mono text-ink-600">
          {{ rawParamCount(row) }} param{{ rawParamCount(row) === 1 ? '' : 's' }}
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
          <input class="input" v-model="name" />
        </div>
        <div>
          <label class="label">Description</label>
          <textarea class="textarea" rows="2" v-model="description" />
        </div>
        <div>
          <label class="label">Algorithm</label>
          <select class="select" v-model="kind" :disabled="!!editing" @change="resetParameters">
            <option v-for="k in kinds" :key="k.kind" :value="k.kind">{{ k.label }}</option>
          </select>
          <p class="text-xs text-ink-500 mt-1">{{ currentKindInfo?.description }}</p>
        </div>

        <div v-if="currentKindInfo" class="space-y-3">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-medium text-ink-700 mr-auto">Parameters</h3>
            <div v-if="supportsSimple" class="inline-flex rounded-lg border border-ink-200 overflow-hidden text-xs">
              <button type="button" class="px-3 py-1"
                :class="paramMode === 'simple' ? 'bg-brand-600 text-white' : 'bg-white text-ink-600'"
                @click="switchMode('simple')">Simple</button>
              <button type="button" class="px-3 py-1"
                :class="paramMode === 'advanced' ? 'bg-brand-600 text-white' : 'bg-white text-ink-600'"
                @click="switchMode('advanced')">Advanced</button>
            </div>
          </div>

          <!-- Simple mode: friendly 1-10 dials -->
          <template v-if="supportsSimple && paramMode === 'simple'">
            <div v-for="p in currentKindInfo.simple_parameters" :key="p.name" class="space-y-1">
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium capitalize">{{ p.name.replace(/_/g, ' ') }}</span>
                <span class="text-xs tabular-nums text-brand-600 font-semibold">{{ simpleParams[p.name] }}/10</span>
              </div>
              <input type="range" min="1" max="10" step="1" class="w-full accent-brand-600"
                     v-model.number="simpleParams[p.name]" @input="refreshEffective" />
              <p class="text-xs text-ink-500">{{ p.description }}</p>
            </div>
            <details class="text-xs text-ink-500">
              <summary class="cursor-pointer select-none hover:text-ink-700">Show resulting math parameters</summary>
              <pre class="mt-2 p-2 bg-ink-50 rounded font-mono overflow-x-auto">{{ effectivePretty }}</pre>
            </details>
          </template>

          <!-- Advanced mode: raw parameters -->
          <template v-else>
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
                v-model.number="advancedParams[p.name]"
              />
            </div>
            <p v-if="currentKindInfo.parameters.length === 0" class="text-xs text-ink-500">
              This strategy has no parameters.
            </p>
          </template>
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

const name = ref('');
const description = ref('');
const kind = ref<StrategyKind>('round_robin');
const paramMode = ref<'simple' | 'advanced'>('advanced');
const simpleParams = ref<Record<string, number>>({});
const advancedParams = ref<Record<string, any>>({});
const effective = ref<Record<string, any>>({});

const currentKindInfo = computed(() => kinds.value.find((k) => k.kind === kind.value));
const supportsSimple = computed(() => (currentKindInfo.value?.simple_parameters.length ?? 0) > 0);
const effectivePretty = computed(() => JSON.stringify(effective.value, null, 2));

const defaultAdvanced = (): Record<string, any> => {
  const o: Record<string, any> = {};
  for (const p of currentKindInfo.value?.parameters ?? []) o[p.name] = p.default;
  return o;
};
const defaultSimple = (): Record<string, number> => {
  const o: Record<string, number> = {};
  for (const p of currentKindInfo.value?.simple_parameters ?? []) o[p.name] = Number(p.default);
  return o;
};

const refreshEffective = async () => {
  if (paramMode.value !== 'simple' || !supportsSimple.value) return;
  try {
    effective.value = await api.previewStrategy({
      kind: kind.value,
      parameters: { mode: 'simple', ...simpleParams.value },
    });
  } catch { /* preview is best-effort */ }
};

const switchMode = async (m: 'simple' | 'advanced') => {
  if (m === paramMode.value) return;
  if (m === 'advanced' && supportsSimple.value) {
    // Carry the dial translation into the advanced fields so nothing is lost.
    try {
      advancedParams.value = (await api.previewStrategy({
        kind: kind.value,
        parameters: { mode: 'simple', ...simpleParams.value },
      })) as Record<string, any>;
    } catch { /* keep current advanced values */ }
  }
  paramMode.value = m;
  if (m === 'simple') refreshEffective();
};

const resetParameters = () => {
  advancedParams.value = defaultAdvanced();
  simpleParams.value = defaultSimple();
  paramMode.value = supportsSimple.value ? 'simple' : 'advanced';
  refreshEffective();
};

const reload = async () => { rows.value = await api.listStrategyConfigs(); };

const kindLabel = (k: StrategyKind) => kinds.value.find((kk) => kk.kind === k)?.label ?? k;
const rawParamCount = (row: StrategyConfig) =>
  Object.keys(row.parameters ?? {}).filter((k) => k !== 'mode').length;

const openCreate = () => {
  editing.value = null;
  name.value = '';
  description.value = '';
  kind.value = 'round_robin';
  resetParameters();
  formOpen.value = true;
};

const openEdit = (row: StrategyConfig) => {
  editing.value = row;
  name.value = row.name;
  description.value = row.description ?? '';
  kind.value = row.kind;
  const params: Record<string, any> = { ...(row.parameters ?? {}) };
  advancedParams.value = defaultAdvanced();
  simpleParams.value = defaultSimple();
  if (params.mode === 'simple' && supportsSimple.value) {
    paramMode.value = 'simple';
    for (const p of currentKindInfo.value?.simple_parameters ?? []) {
      if (params[p.name] != null) simpleParams.value[p.name] = Number(params[p.name]);
    }
    refreshEffective();
  } else {
    paramMode.value = 'advanced';
    delete params.mode;
    advancedParams.value = { ...defaultAdvanced(), ...params };
  }
  formOpen.value = true;
};

const submit = async () => {
  saving.value = true; error.value = '';
  try {
    const parameters =
      paramMode.value === 'simple' && supportsSimple.value
        ? { mode: 'simple', ...simpleParams.value }
        : { ...advancedParams.value };
    const payload: any = {
      name: name.value,
      description: description.value || null,
      parameters,
    };
    if (!editing.value) payload.kind = kind.value;
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
