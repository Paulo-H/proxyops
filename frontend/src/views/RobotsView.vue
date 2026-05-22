<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-ink-800">Robots</h1>
      <button class="btn-primary" @click="openCreate" :disabled="!auth.canEdit">+ New robot</button>
    </div>

    <DataTable
      :rows="rows"
      :columns="[
        { key: 'name', label: 'Name' },
        { key: 'description', label: 'Description' },
        { key: 'api_key', label: 'API key' },
        { key: 'groups', label: 'Bound groups' },
        { key: 'lease', label: 'Lease' },
        { key: 'is_active', label: 'Active' },
      ]"
      :row-key="(r) => r.id"
      emptyText="No robots registered yet."
    >
      <template #cell-api_key="{ row }">
        <span class="font-mono text-xs text-ink-500">{{ row.api_key_prefix }}…</span>
      </template>
      <template #cell-groups="{ row }">
        <span v-if="row.group_ids.length === 0" class="text-ink-400 text-sm">— Any group —</span>
        <span v-else class="flex flex-wrap gap-1">
          <span v-for="gid in row.group_ids" :key="gid" class="badge-info">
            {{ groupName(gid) }}
          </span>
        </span>
      </template>
      <template #cell-lease="{ row }">
        <span class="text-sm tabular-nums">{{ row.default_lease_minutes }} min</span>
      </template>
      <template #cell-is_active="{ row }">
        <span v-if="row.is_active" class="badge-success">Active</span>
        <span v-else class="badge-muted">Disabled</span>
      </template>
      <template #actions="{ row }">
        <button class="btn-ghost text-sm" @click="openEdit(row)" :disabled="!auth.canEdit">Edit</button>
        <button class="btn-ghost text-sm" @click="rotateKey(row)" :disabled="!auth.canEdit">Rotate key</button>
        <button class="btn-ghost text-sm text-red-600" @click="onDelete(row)" :disabled="!auth.canEdit">Delete</button>
      </template>
    </DataTable>

    <Modal v-model="formOpen" :title="editing ? 'Edit robot' : 'New robot'">
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
          <label class="label">Default lease (minutes)</label>
          <input class="input" type="number" min="1" max="240" v-model.number="form.default_lease_minutes" />
        </div>
        <div>
          <label class="label">Bound groups</label>
          <div class="border border-ink-200 rounded-lg max-h-48 overflow-y-auto p-2">
            <label v-for="g in groups" :key="g.id" class="flex items-center gap-2 text-sm py-0.5">
              <input type="checkbox" :value="g.id" v-model="form.group_ids" />
              {{ g.name }}
              <span class="text-ink-400 text-xs">({{ g.proxy_count }} proxies)</span>
            </label>
            <p v-if="groups.length === 0" class="text-ink-400 text-sm">No groups yet.</p>
          </div>
          <p class="text-xs text-ink-500 mt-1">Leave empty to allow any group.</p>
        </div>
        <label class="inline-flex items-center gap-2">
          <input type="checkbox" v-model="form.is_active" />
          <span class="text-sm">Active</span>
        </label>
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="formOpen = false">Cancel</button>
        <button class="btn-primary" @click="submit" :disabled="saving">Save</button>
      </template>
    </Modal>

    <Modal v-model="keyOpen" title="Robot API key">
      <p class="text-sm text-ink-600 mb-3">
        Copy this key now — it will not be shown again. Use it as the
        <code class="font-mono text-xs">X-Robot-Key</code> header.
      </p>
      <div class="p-3 bg-ink-50 rounded-lg font-mono text-sm break-all">{{ revealedKey }}</div>
      <template #footer>
        <button class="btn-primary" @click="keyOpen = false">Done</button>
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
import type { Robot, ProxyGroup } from '@/api/types';

const auth = useAuthStore();
const rows = ref<Robot[]>([]);
const groups = ref<ProxyGroup[]>([]);

const formOpen = ref(false);
const editing = ref<Robot | null>(null);
const saving = ref(false);
const error = ref('');

const keyOpen = ref(false);
const revealedKey = ref('');

const emptyForm = () => ({
  name: '',
  description: '',
  default_lease_minutes: 5,
  group_ids: [] as number[],
  is_active: true,
});
const form = ref(emptyForm());

const reload = async () => { rows.value = await api.listRobots(); };
const groupName = (id: number) => groups.value.find((g) => g.id === id)?.name ?? `#${id}`;

const openCreate = () => { editing.value = null; form.value = emptyForm(); formOpen.value = true; };
const openEdit = (row: Robot) => {
  editing.value = row;
  form.value = {
    name: row.name,
    description: row.description ?? '',
    default_lease_minutes: row.default_lease_minutes,
    group_ids: [...row.group_ids],
    is_active: row.is_active,
  };
  formOpen.value = true;
};

const submit = async () => {
  saving.value = true;
  error.value = '';
  const payload: any = { ...form.value, description: form.value.description || null };
  try {
    if (editing.value) {
      await api.updateRobot(editing.value.id, payload);
    } else {
      const created = await api.createRobot(payload);
      revealedKey.value = created.api_key ?? '';
      keyOpen.value = true;
    }
    formOpen.value = false;
    await reload();
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? 'Failed to save.';
  } finally {
    saving.value = false;
  }
};

const rotateKey = async (row: Robot) => {
  if (!confirm(`Generate a new API key for "${row.name}"? The old one will stop working immediately.`)) return;
  const updated = await api.rotateRobotKey(row.id);
  revealedKey.value = updated.api_key ?? '';
  keyOpen.value = true;
};

const onDelete = async (row: Robot) => {
  if (!confirm(`Delete robot "${row.name}"?`)) return;
  await api.deleteRobot(row.id);
  await reload();
};

onMounted(async () => {
  groups.value = await api.listGroups();
  await reload();
});
</script>
