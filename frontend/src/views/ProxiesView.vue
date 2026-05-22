<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between flex-wrap gap-2">
      <h1 class="text-xl font-semibold text-ink-800">Proxies</h1>
      <div class="flex gap-2">
        <button class="btn-secondary" @click="bulkOpen = true" :disabled="!auth.canEdit">Bulk import</button>
        <button class="btn-primary" @click="openCreate" :disabled="!auth.canEdit">+ New proxy</button>
      </div>
    </div>

    <DataTable
      :rows="rows"
      :columns="[
        { key: 'host', label: 'Host' },
        { key: 'port', label: 'Port' },
        { key: 'protocol', label: 'Protocol' },
        { key: 'provider_name', label: 'Provider' },
        { key: 'groups', label: 'Groups' },
        { key: 'status', label: 'Status' },
        { key: 'expires_at', label: 'Expires' },
        { key: 'success_rate', label: 'Success' },
      ]"
      :row-key="(r) => r.id"
      emptyText="No proxies yet."
    >
      <template #toolbar>
        <input class="input max-w-xs" v-model="filters.search" placeholder="Search host/username" @input="reload" />
        <select class="select max-w-xs" v-model="filters.provider_id" @change="reload">
          <option :value="null">All providers</option>
          <option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <select class="select max-w-xs" v-model="filters.group_id" @change="reload">
          <option :value="null">All groups</option>
          <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
        <select class="select max-w-[10rem]" v-model="filters.expiring_in_days" @change="reload">
          <option :value="null">Any expiry</option>
          <option :value="7">≤ 7 days</option>
          <option :value="30">≤ 30 days</option>
          <option :value="90">≤ 90 days</option>
        </select>
      </template>
      <template #cell-status="{ row }">
        <span v-if="!row.is_active" class="badge-muted">Disabled</span>
        <span v-else-if="row.is_in_use" class="badge-warn">In use</span>
        <span v-else class="badge-success">Active</span>
      </template>
      <template #cell-expires_at="{ row }">
        <span v-if="row.expires_at" :class="expiryClass(row.expires_at)">{{ formatDate(row.expires_at) }}</span>
        <span v-else class="text-ink-400">never</span>
      </template>
      <template #cell-success_rate="{ row }">
        <div class="flex items-center gap-2">
          <div class="w-16 h-1.5 rounded-full bg-ink-100 overflow-hidden">
            <div class="h-full bg-brand-500" :style="`width:${Math.round(row.success_rate * 100)}%`" />
          </div>
          <span class="text-xs text-ink-600 tabular-nums">{{ (row.success_rate * 100).toFixed(0) }}%</span>
        </div>
      </template>
      <template #cell-groups="{ row }">
        <span class="text-xs text-ink-500">{{ row.group_ids.length }} group{{ row.group_ids.length === 1 ? '' : 's' }}</span>
      </template>
      <template #actions="{ row }">
        <button class="btn-ghost text-sm" @click="openEdit(row)" :disabled="!auth.canEdit">Edit</button>
        <button v-if="row.is_in_use" class="btn-ghost text-sm" @click="unlock(row)" :disabled="!auth.canEdit">Unlock</button>
        <button class="btn-ghost text-sm text-red-600" @click="onDelete(row)" :disabled="!auth.canEdit">Delete</button>
      </template>
    </DataTable>

    <Modal v-model="formOpen" :title="editing ? 'Edit proxy' : 'New proxy'">
      <div class="grid grid-cols-2 gap-3">
        <div class="col-span-2">
          <label class="label">Host</label>
          <input class="input" v-model="form.host" placeholder="1.2.3.4 or proxy.example.com" />
        </div>
        <div>
          <label class="label">Port</label>
          <input class="input" type="number" min="1" max="65535" v-model.number="form.port" />
        </div>
        <div>
          <label class="label">Protocol</label>
          <select class="select" v-model="form.protocol">
            <option value="http">http</option>
            <option value="https">https</option>
            <option value="socks4">socks4</option>
            <option value="socks5">socks5</option>
          </select>
        </div>
        <div>
          <label class="label">Username</label>
          <input class="input" v-model="form.username" />
        </div>
        <div>
          <label class="label">Password</label>
          <input class="input" type="password" v-model="form.password" />
        </div>
        <div class="col-span-2">
          <label class="label">Provider</label>
          <select class="select" v-model="form.provider_id">
            <option :value="null">— None —</option>
            <option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div class="col-span-2">
          <label class="label">Groups</label>
          <div class="flex flex-wrap gap-2">
            <label v-for="g in groups" :key="g.id" class="inline-flex items-center gap-1 text-sm">
              <input type="checkbox" :value="g.id" v-model="form.group_ids" />
              {{ g.name }}
            </label>
            <span v-if="groups.length === 0" class="text-ink-400 text-sm">No groups yet.</span>
          </div>
        </div>
        <div>
          <label class="label">Expires at</label>
          <input class="input" type="datetime-local" v-model="form.expires_at" />
        </div>
        <div class="flex items-end">
          <label class="inline-flex items-center gap-2">
            <input type="checkbox" v-model="form.is_active" />
            <span class="text-sm">Active</span>
          </label>
        </div>
        <p v-if="error" class="col-span-2 text-sm text-red-600">{{ error }}</p>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="formOpen = false">Cancel</button>
        <button class="btn-primary" @click="submit" :disabled="saving">Save</button>
      </template>
    </Modal>

    <Modal v-model="bulkOpen" title="Bulk import">
      <p class="text-sm text-ink-600 mb-2">
        Paste one proxy per line as <code class="font-mono text-xs">host:port</code> or
        <code class="font-mono text-xs">host:port:user:pass</code>.
      </p>
      <textarea class="textarea" rows="8" v-model="bulkText" placeholder="1.2.3.4:8080
5.6.7.8:1080:user:pass"></textarea>
      <div class="grid grid-cols-2 gap-3 mt-3">
        <div>
          <label class="label">Provider</label>
          <select class="select" v-model="bulkProvider">
            <option :value="null">— None —</option>
            <option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">Default protocol</label>
          <select class="select" v-model="bulkProtocol">
            <option value="http">http</option>
            <option value="https">https</option>
            <option value="socks4">socks4</option>
            <option value="socks5">socks5</option>
          </select>
        </div>
        <div class="col-span-2">
          <label class="label">Groups</label>
          <div class="flex flex-wrap gap-2">
            <label v-for="g in groups" :key="g.id" class="inline-flex items-center gap-1 text-sm">
              <input type="checkbox" :value="g.id" v-model="bulkGroupIds" />
              {{ g.name }}
            </label>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="bulkOpen = false">Cancel</button>
        <button class="btn-primary" @click="submitBulk" :disabled="bulkSaving">Import</button>
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
import type { Proxy, Provider, ProxyGroup, ProxyProtocol } from '@/api/types';

const auth = useAuthStore();
const rows = ref<Proxy[]>([]);
const providers = ref<Provider[]>([]);
const groups = ref<ProxyGroup[]>([]);

const filters = ref<{ search: string; provider_id: number | null; group_id: number | null; expiring_in_days: number | null }>({
  search: '',
  provider_id: null,
  group_id: null,
  expiring_in_days: null,
});

const formOpen = ref(false);
const editing = ref<Proxy | null>(null);
const saving = ref(false);
const error = ref('');

interface ProxyForm {
  host: string;
  port: number;
  protocol: ProxyProtocol;
  username: string;
  password: string;
  provider_id: number | null;
  group_ids: number[];
  expires_at: string;
  is_active: boolean;
}
const emptyForm = (): ProxyForm => ({
  host: '',
  port: 8080,
  protocol: 'http',
  username: '',
  password: '',
  provider_id: null,
  group_ids: [],
  expires_at: '',
  is_active: true,
});
const form = ref<ProxyForm>(emptyForm());

const bulkOpen = ref(false);
const bulkText = ref('');
const bulkProvider = ref<number | null>(null);
const bulkProtocol = ref<'http' | 'https' | 'socks4' | 'socks5'>('http');
const bulkGroupIds = ref<number[]>([]);
const bulkSaving = ref(false);

const reload = async () => {
  rows.value = await api.listProxies({
    search: filters.value.search || undefined,
    provider_id: filters.value.provider_id ?? undefined,
    group_id: filters.value.group_id ?? undefined,
    expiring_in_days: filters.value.expiring_in_days ?? undefined,
  });
};

const openCreate = () => { editing.value = null; form.value = emptyForm(); formOpen.value = true; };
const openEdit = (row: Proxy) => {
  editing.value = row;
  form.value = {
    host: row.host,
    port: row.port,
    protocol: row.protocol,
    username: row.username ?? '',
    password: '',
    provider_id: row.provider_id,
    group_ids: [...row.group_ids],
    expires_at: row.expires_at ? row.expires_at.slice(0, 16) : '',
    is_active: row.is_active,
  };
  formOpen.value = true;
};

const submit = async () => {
  saving.value = true;
  error.value = '';
  const payload: any = {
    host: form.value.host,
    port: form.value.port,
    protocol: form.value.protocol,
    username: form.value.username || null,
    provider_id: form.value.provider_id,
    group_ids: form.value.group_ids,
    expires_at: form.value.expires_at ? new Date(form.value.expires_at).toISOString() : null,
    is_active: form.value.is_active,
  };
  if (form.value.password) payload.password = form.value.password;
  try {
    if (editing.value) await api.updateProxy(editing.value.id, payload);
    else await api.createProxy(payload);
    formOpen.value = false;
    await reload();
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? 'Failed to save.';
  } finally {
    saving.value = false;
  }
};

const submitBulk = async () => {
  bulkSaving.value = true;
  try {
    const proxies = bulkText.value
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
      .map((line) => {
        const [host, portStr, username, password] = line.split(':');
        return {
          host,
          port: parseInt(portStr, 10),
          protocol: bulkProtocol.value,
          username: username || null,
          password: password || null,
        };
      })
      .filter((p) => p.host && Number.isFinite(p.port));
    if (!proxies.length) return;
    await api.bulkCreateProxies({
      provider_id: bulkProvider.value,
      group_ids: bulkGroupIds.value,
      proxies,
    });
    bulkOpen.value = false;
    bulkText.value = '';
    await reload();
  } finally {
    bulkSaving.value = false;
  }
};

const onDelete = async (row: Proxy) => {
  if (!confirm(`Delete proxy ${row.host}:${row.port}?`)) return;
  await api.deleteProxy(row.id);
  await reload();
};

const unlock = async (row: Proxy) => {
  await api.unlockProxy(row.id);
  await reload();
};

const formatDate = (iso: string) => new Date(iso).toLocaleString();
const expiryClass = (iso: string) => {
  const diffDays = (new Date(iso).getTime() - Date.now()) / (1000 * 60 * 60 * 24);
  if (diffDays < 0) return 'text-red-600 font-medium';
  if (diffDays < 7) return 'text-amber-600 font-medium';
  return 'text-ink-700';
};

onMounted(async () => {
  [providers.value, groups.value] = await Promise.all([api.listProviders(), api.listGroups()]);
  await reload();
});
</script>
