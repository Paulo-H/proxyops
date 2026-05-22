<template>
  <div class="space-y-6 max-w-2xl">
    <div>
      <h1 class="text-xl font-semibold text-ink-800">Settings</h1>
      <p class="text-sm text-ink-600">Manage your account.</p>
    </div>

    <div class="card p-5">
      <h2 class="font-medium text-ink-700 mb-3">Profile</h2>
      <dl class="grid grid-cols-3 gap-2 text-sm">
        <dt class="text-ink-500">Email</dt><dd class="col-span-2">{{ auth.user?.email }}</dd>
        <dt class="text-ink-500">Name</dt><dd class="col-span-2">{{ auth.user?.full_name ?? '—' }}</dd>
        <dt class="text-ink-500">Role</dt><dd class="col-span-2"><span class="badge-info">{{ auth.user?.role }}</span></dd>
      </dl>
    </div>

    <div class="card p-5">
      <h2 class="font-medium text-ink-700 mb-3">Change password</h2>
      <form class="space-y-3" @submit.prevent="submit">
        <div>
          <label class="label">Current password</label>
          <input class="input" type="password" v-model="form.current_password" required />
        </div>
        <div>
          <label class="label">New password</label>
          <input class="input" type="password" v-model="form.new_password" required minlength="8" />
        </div>
        <p v-if="message" class="text-sm" :class="error ? 'text-red-600' : 'text-emerald-600'">{{ message }}</p>
        <button class="btn-primary" :disabled="saving">Update password</button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { api } from '@/api';
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
const form = ref({ current_password: '', new_password: '' });
const saving = ref(false);
const message = ref('');
const error = ref(false);

const submit = async () => {
  saving.value = true; message.value = ''; error.value = false;
  try {
    await api.changePassword(form.value);
    message.value = 'Password updated.';
    form.value = { current_password: '', new_password: '' };
  } catch (e: any) {
    error.value = true;
    message.value = e?.response?.data?.detail ?? 'Failed to update password.';
  } finally {
    saving.value = false;
  }
};
</script>
