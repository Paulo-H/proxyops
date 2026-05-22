<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-ink-800">Providers</h1>
      <button class="btn-primary" @click="openCreate" :disabled="!auth.canEdit">
        + New provider
      </button>
    </div>

    <DataTable
      :rows="rows"
      :columns="[
        { key: 'name', label: 'Name' },
        { key: 'website', label: 'Website' },
        { key: 'contact_email', label: 'Contact' },
        { key: 'proxy_count', label: 'Proxies' },
      ]"
      :row-key="(r) => r.id"
      emptyText="No providers yet."
    >
      <template #cell-website="{ row }">
        <a v-if="row.website" :href="row.website" target="_blank" rel="noopener" class="text-brand-600 hover:underline">
          {{ row.website }}
        </a>
        <span v-else class="text-ink-400">—</span>
      </template>
      <template #actions="{ row }">
        <button class="btn-ghost text-sm" @click="openEdit(row)" :disabled="!auth.canEdit">Edit</button>
        <button class="btn-ghost text-sm text-red-600" @click="onDelete(row)" :disabled="!auth.canEdit">Delete</button>
      </template>
    </DataTable>

    <Modal v-model="formOpen" :title="editing ? 'Edit provider' : 'New provider'">
      <div class="space-y-3">
        <div>
          <label class="label">Name</label>
          <input class="input" v-model="form.name" />
        </div>
        <div>
          <label class="label">Website</label>
          <input class="input" v-model="form.website" placeholder="https://" />
        </div>
        <div>
          <label class="label">Contact email</label>
          <input class="input" v-model="form.contact_email" />
        </div>
        <div>
          <label class="label">Notes</label>
          <textarea class="textarea" rows="3" v-model="form.notes" />
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
import type { Provider } from '@/api/types';
import { useAuthStore } from '@/stores/auth';
import DataTable from '@/components/ui/DataTable.vue';
import Modal from '@/components/ui/Modal.vue';

const auth = useAuthStore();
const rows = ref<Provider[]>([]);
const formOpen = ref(false);
const editing = ref<Provider | null>(null);
const saving = ref(false);
const error = ref('');

const form = ref({ name: '', website: '', contact_email: '', notes: '' });

const reload = async () => { rows.value = await api.listProviders(); };

const openCreate = () => {
  editing.value = null;
  form.value = { name: '', website: '', contact_email: '', notes: '' };
  formOpen.value = true;
};
const openEdit = (row: Provider) => {
  editing.value = row;
  form.value = {
    name: row.name,
    website: row.website ?? '',
    contact_email: row.contact_email ?? '',
    notes: row.notes ?? '',
  };
  formOpen.value = true;
};

const submit = async () => {
  saving.value = true;
  error.value = '';
  const payload: any = {
    name: form.value.name,
    website: form.value.website || null,
    contact_email: form.value.contact_email || null,
    notes: form.value.notes || null,
  };
  try {
    if (editing.value) await api.updateProvider(editing.value.id, payload);
    else await api.createProvider(payload);
    formOpen.value = false;
    await reload();
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? 'Failed to save.';
  } finally {
    saving.value = false;
  }
};

const onDelete = async (row: Provider) => {
  if (!confirm(`Delete provider "${row.name}"? Its proxies will lose the link.`)) return;
  await api.deleteProvider(row.id);
  await reload();
};

onMounted(reload);
</script>
