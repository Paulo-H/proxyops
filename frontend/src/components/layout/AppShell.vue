<template>
  <div class="flex h-screen overflow-hidden bg-ink-50">
    <!-- Sidebar -->
    <aside
      :class="[
        'fixed inset-y-0 left-0 z-30 w-64 bg-brand-950 text-ink-100 transform transition-transform duration-200',
        'lg:relative lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
      ]"
    >
      <div class="flex items-center gap-2 h-16 px-5 border-b border-brand-900">
        <img :src="logoUrl" alt="ProxyOps" class="w-8 h-8" />
        <div class="font-semibold tracking-tight text-white">
          Proxy<span class="text-brand-400">Ops</span>
        </div>
      </div>
      <nav class="px-3 py-4 space-y-0.5">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          v-slot="{ isActive }"
          custom
        >
          <a
            :href="item.to"
            @click.prevent="goTo(item.to)"
            :class="[
              'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition',
              isActive
                ? 'bg-brand-600/20 text-white border-l-2 border-brand-400'
                : 'text-ink-200 hover:bg-brand-900/50 hover:text-white',
            ]"
          >
            <span class="text-brand-300" v-html="item.icon"></span>
            {{ item.label }}
          </a>
        </RouterLink>
      </nav>
      <div class="absolute bottom-0 left-0 right-0 px-5 py-3 text-xs text-ink-400 border-t border-brand-900">
        ProxyOps v0.1.0
      </div>
    </aside>

    <!-- Backdrop on mobile -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-black/40 z-20 lg:hidden"
      @click="sidebarOpen = false"
    />

    <!-- Main column -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <header class="h-16 bg-white border-b border-ink-100 flex items-center px-4 lg:px-6 gap-3">
        <button class="btn-ghost lg:hidden" @click="sidebarOpen = !sidebarOpen" aria-label="Toggle menu">
          <svg viewBox="0 0 20 20" class="w-5 h-5"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        <div class="font-semibold text-ink-700 truncate">
          {{ pageTitle }}
        </div>
        <div class="ml-auto flex items-center gap-2">
          <span class="hidden sm:inline-flex badge-info">{{ auth.user?.role }}</span>
          <div class="hidden sm:block text-sm text-ink-600">{{ auth.user?.email }}</div>
          <button class="btn-secondary" @click="logout">Sign out</button>
        </div>
      </header>
      <main class="flex-1 overflow-y-auto p-4 lg:p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

// Public asset: reference at runtime so Rollup doesn't try to resolve it as a
// module at build time (files in public/ are not module-resolvable).
const logoUrl = `${import.meta.env.BASE_URL}logo-icon.png`;

const sidebarOpen = ref(false);

const navItems = computed(() => {
  const items = [
    { to: '/dashboard',  label: 'Dashboard',  icon: icons.dashboard },
    { to: '/proxies',    label: 'Proxies',    icon: icons.proxy },
    { to: '/providers',  label: 'Providers',  icon: icons.providers },
    { to: '/groups',     label: 'Groups',     icon: icons.groups },
    { to: '/robots',     label: 'Robots',     icon: icons.robots },
    { to: '/domains',    label: 'Domains',    icon: icons.domains },
    { to: '/strategies', label: 'Strategies', icon: icons.strategies },
    { to: '/logs',       label: 'Request log',icon: icons.logs },
  ];
  if (auth.isAdmin) items.push({ to: '/users', label: 'Users', icon: icons.users });
  items.push({ to: '/settings', label: 'Settings', icon: icons.settings });
  return items;
});

const pageTitle = computed(() => {
  const it = navItems.value.find((i) => route.path.startsWith(i.to));
  return it ? it.label : 'ProxyOps';
});

const goTo = (to: string) => {
  sidebarOpen.value = false;
  router.push(to);
};

const logout = () => {
  auth.logout();
  router.replace({ name: 'login' });
};

const icons = {
  dashboard:  '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M3 3h6v8H3V3zm0 10h6v4H3v-4zm8-10h6v4h-6V3zm0 6h6v8h-6V9z"/></svg>',
  proxy:      '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M10 2a4 4 0 100 8 4 4 0 000-8zM2 18a8 8 0 0116 0H2z"/></svg>',
  providers:  '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M2 5h16v3H2V5zm0 7h16v3H2v-3z"/></svg>',
  groups:     '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M7 8a3 3 0 110-6 3 3 0 010 6zm6 0a3 3 0 110-6 3 3 0 010 6zm-6 1c-3 0-5 1.5-5 3v2h10v-2c0-1.5-2-3-5-3zm6 0c-.6 0-1.1.05-1.6.15.96.83 1.6 1.85 1.6 2.85v2h6v-2c0-1.5-2-3-6-3z"/></svg>',
  robots:     '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M4 6h12a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V8a2 2 0 012-2zm3 4a1 1 0 100 2 1 1 0 000-2zm6 0a1 1 0 100 2 1 1 0 000-2zM9 2h2v3H9V2z"/></svg>',
  domains:    '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 2c.7 0 1.7 1 2.3 3H7.7C8.3 5 9.3 4 10 4zm-3.3 5h6.6c.1.6.2 1.3.2 2 0 .7-.1 1.4-.2 2H6.7c-.1-.6-.2-1.3-.2-2 0-.7.1-1.4.2-2zM10 16c-.7 0-1.7-1-2.3-3h4.6c-.6 2-1.6 3-2.3 3z"/></svg>',
  strategies: '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M3 17h14v-2H3v2zm2-4h4V5H5v8zm5 0h4V8h-4v5zm5 0h2v-3h-2v3z"/></svg>',
  logs:       '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M4 2h9l5 5v11a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1zm8 1.5V8h4.5L12 3.5z"/></svg>',
  users:      '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M10 10a4 4 0 100-8 4 4 0 000 8zM3 18a7 7 0 0114 0H3z"/></svg>',
  settings:   '<svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M10 6.5A3.5 3.5 0 1010 13.5 3.5 3.5 0 0010 6.5zm7 3.5a7 7 0 00-.1-1.2l2-1.5-2-3.5-2.4.9a7 7 0 00-2.1-1.2L12 0H8l-.4 2.5a7 7 0 00-2.1 1.2L3.1 2.8l-2 3.5 2 1.5A7 7 0 003 10c0 .4 0 .8.1 1.2l-2 1.5 2 3.5 2.4-.9a7 7 0 002.1 1.2L8 20h4l.4-2.5a7 7 0 002.1-1.2l2.4.9 2-3.5-2-1.5c0-.4.1-.8.1-1.2z"/></svg>',
};
</script>
