<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-ink-800">Users</h1>
      <button class="btn-primary" @click="openCreate">+ New user</button>
    </div>

    <DataTable
      :rows="rows"
      :columns="[
        { key: 'email', label: 'Email' },
        { key: 'full_name', label: 'Name' },
        { key: 'role', label: 'Role' },
        { key: 'is_active', label: 'Active' },
      ]"
      :row-key="(r) => r.id"
      emptyText="No users."
    >
      <template #cell-role="{ row }">
        <span class="badge-info">{{ row.role }}</span>
      </template>
      <template #cell-is_active="{ row }">
        <span v-if="row.is_active" class="badge-success">Yes</span>
        <span v-else class="badge-muted">No</span>
      </template>
      <template #actions="{ row }">
        <button class="btn-ghost text-sm" @click="openEdit(row)">Edit</button>
        <button class="btn-ghost text-sm text-red-600" @click="onDelete(row)">Delete</button>
      </template>
    </DataTable>

    <Modal v-model="formOpen" :title="editing ? 'Edit user' : 'New user'">
      <div class="space-y-3">
        <div>
          <label class="label">Email</label>
          <input class="input" v-model="form.email" :disabled="!!editing" type="email" />
        </div>
        <div>
          <label class="label">Full name</label>
          <input class="input" v-model="form.full_name" />
        </div>
        <div>
          <label class="label">Role</label>
          <select class="select" v-model="form.role">
            <option value="admin">admin</option>
            <option value="operator">operator</option>
            <option value="viewer">viewer</option>
          </select>
        </div>
        <div v-if="!editing">
          <label class="label">Initial password</label>
          <input class="input" type="password" v-model="form.password" />
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '@/api';
import DataTable from '@/components/ui/DataTable.vue';
import Modal from '@/components/ui/Modal.vue';
import type { User, UserRole } from '@/api/types';

const rows = ref<User[]>([]);
const formOpen = ref(false);
const editing = ref<User | null>(null);
const saving = ref(false);
const error = ref('');

const form = ref<{ email: string; full_name: string; role: UserRole; password: string; is_active: boolean }>({
  email: '', full_name: '', role: 'operator', password: '', is_active: true,
});

const reload = async () => { rows.value = await api.listUsers(); };

const openCreate = () => {
  editing.value = null;
  form.value = { email: '', full_name: '', role: 'operator', password: '', is_active: true };
  formOpen.value = true;
};
const openEdit = (row: User) => {
  editing.value = row;
  form.value = { email: row.email, full_name: row.full_name ?? '', role: row.role, password: '', is_active: row.is_active };
  formOpen.value = true;
};

const submit = async () => {
  saving.value = true; error.value = '';
  try {
    if (editing.value) {
      await api.updateUser(editing.value.id, {
        full_name: form.value.full_name || null,
        role: form.value.role,
        is_active: form.value.is_active,
      });
    } else {
      await api.createUser({
        email: form.value.email,
        full_name: form.value.full_name || null,
        role: form.value.role,
        is_active: form.value.is_active,
        password: form.value.password,
      });
    }
    formOpen.value = false;
    await reload();
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? 'Failed to save.';
  } finally {
    saving.value = false;
  }
};

const onDelete = async (row: User) => {
  if (!confirm(`Delete user ${row.email}?`)) return;
  await api.deleteUser(row.id);
  await reload();
};

onMounted(reload);
</script>
