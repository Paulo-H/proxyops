<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-ink-800">Domains</h1>
      <button class="btn-primary" @click="openCreate" :disabled="!auth.canEdit">+ New domain</button>
    </div>

    <DataTable
      :rows="rows"
      :columns="[
        { key: 'hostname', label: 'Hostname' },
        { key: 'rate_limit_per_minute', label: 'Rate limit / min' },
        { key: 'is_blocked', label: 'Status' },
        { key: 'notes', label: 'Notes' },
      ]"
      :row-key="(r) => r.id"
      emptyText="No domains tracked."
    >
      <template #cell-rate_limit_per_minute="{ row }">
        <span v-if="row.rate_limit_per_minute" class="tabular-nums">{{ row.rate_limit_per_minute }}</span>
        <span v-else class="text-ink-400">—</span>
      </template>
      <template #cell-is_blocked="{ row }">
        <span v-if="row.is_blocked" class="badge-danger">Blocked</span>
        <span v-else class="badge-success">Allowed</span>
      </template>
      <template #actions="{ row }">
        <button class="btn-ghost text-sm" @click="openEdit(row)" :disabled="!auth.canEdit">Edit</button>
        <button class="btn-ghost text-sm text-red-600" @click="onDelete(row)" :disabled="!auth.canEdit">Delete</button>
      </template>
    </DataTable>

    <Modal v-model="formOpen" :title="editing ? 'Edit domain' : 'New domain'">
      <div class="space-y-3">
        <div>
          <label class="label">Hostname</label>
          <input class="input" v-model="form.hostname" placeholder="example.com" :disabled="!!editing" />
        </div>
        <div>
          <label class="label">Rate limit per minute</label>
          <input class="input" type="number" min="1" v-model.number="form.rate_limit_per_minute" />
        </div>
        <div>
          <label class="label">Notes</label>
          <textarea class="textarea" rows="2" v-model="form.notes" />
        </div>
        <label class="inline-flex items-center gap-2">
          <input type="checkbox" v-model="form.is_blocked" />
          <span class="text-sm">Mark as blocked</span>
        </label>
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
import type { Domain } from '@/api/types';

const auth = useAuthStore();
const rows = ref<Domain[]>([]);
const formOpen = ref(false);
const editing = ref<Domain | null>(null);
const saving = ref(false);
const error = ref('');

const emptyForm = () => ({
  hostname: '',
  rate_limit_per_minute: null as number | null,
  notes: '',
  is_blocked: false,
});
const form = ref(emptyForm());

const reload = async () => { rows.value = await api.listDomains(); };

const openCreate = () => { editing.value = null; form.value = emptyForm(); formOpen.value = true; };
const openEdit = (row: Domain) => {
  editing.value = row;
  form.value = {
    hostname: row.hostname,
    rate_limit_per_minute: row.rate_limit_per_minute,
    notes: row.notes ?? '',
    is_blocked: row.is_blocked,
  };
  formOpen.value = true;
};

const submit = async () => {
  saving.value = true; error.value = '';
  try {
    const payload: any = {
      notes: form.value.notes || null,
      rate_limit_per_minute: form.value.rate_limit_per_minute || null,
      is_blocked: form.value.is_blocked,
    };
    if (!editing.value) payload.hostname = form.value.hostname;
    if (editing.value) await api.updateDomain(editing.value.id, payload);
    else await api.createDomain(payload);
    formOpen.value = false;
    await reload();
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? 'Failed to save.';
  } finally {
    saving.value = false;
  }
};

const onDelete = async (row: Domain) => {
  if (!confirm(`Delete domain "${row.hostname}"?`)) return;
  await api.deleteDomain(row.id);
  await reload();
};

onMounted(reload);
</script>
