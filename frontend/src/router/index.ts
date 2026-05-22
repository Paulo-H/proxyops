import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppShell.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
      { path: 'proxies',   name: 'proxies',   component: () => import('@/views/ProxiesView.vue') },
      { path: 'providers', name: 'providers', component: () => import('@/views/ProvidersView.vue') },
      { path: 'groups',    name: 'groups',    component: () => import('@/views/GroupsView.vue') },
      { path: 'robots',    name: 'robots',    component: () => import('@/views/RobotsView.vue') },
      { path: 'domains',   name: 'domains',   component: () => import('@/views/DomainsView.vue') },
      { path: 'strategies',name: 'strategies',component: () => import('@/views/StrategiesView.vue') },
      { path: 'logs',      name: 'logs',      component: () => import('@/views/LogsView.vue') },
      { path: 'users',     name: 'users',     component: () => import('@/views/UsersView.vue'),
        meta: { adminOnly: true } },
      { path: 'settings',  name: 'settings',  component: () => import('@/views/SettingsView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { next: to.fullPath } };
  }
  if (to.meta.public && auth.isAuthenticated && to.name === 'login') {
    return { name: 'dashboard' };
  }
  if (to.meta.adminOnly && !auth.isAdmin) {
    return { name: 'dashboard' };
  }
});

export default router;
