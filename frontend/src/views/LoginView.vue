<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-950 via-brand-900 to-ink-900 px-4">
    <div class="w-full max-w-md card p-8">
      <div class="flex flex-col items-center mb-8">
        <img :src="logoUrl" class="w-56 h-auto mb-2" alt="ProxyOps" />
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <div>
          <label class="label" for="email">Email</label>
          <input id="email" v-model="email" type="email" required autocomplete="email" class="input" />
        </div>
        <div>
          <label class="label" for="password">Password</label>
          <input id="password" v-model="password" type="password" required autocomplete="current-password" class="input" />
        </div>
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        <button class="btn-primary w-full" :disabled="loading">
          <span v-if="loading">Signing in…</span>
          <span v-else>Sign in</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const logoUrl = `${import.meta.env.BASE_URL}logo.png`;
const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

const submit = async () => {
  loading.value = true;
  error.value = '';
  try {
    await auth.login(email.value, password.value);
    router.replace((route.query.next as string) || '/dashboard');
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'Failed to sign in.';
  } finally {
    loading.value = false;
  }
};
</script>
