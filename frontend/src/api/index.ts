import { http } from './http';
import type {
  Domain,
  MetricsFilters,
  MetricsSummary,
  Provider,
  Proxy,
  ProxyGroup,
  RequestLog,
  Robot,
  StatusCodeBucket,
  StrategyConfig,
  StrategyKindInfo,
  TimeseriesPoint,
  TopItem,
  User,
} from './types';

export const api = {
  // ---------- auth ----------
  login(email: string, password: string) {
    return http.post<{ access_token: string; refresh_token: string }>('/auth/login', { email, password }).then((r) => r.data);
  },
  refresh(token: string) {
    return http.post<{ access_token: string; refresh_token: string }>(
      `/auth/refresh?refresh_token=${encodeURIComponent(token)}`,
    ).then((r) => r.data);
  },
  me() {
    return http.get<User>('/auth/me').then((r) => r.data);
  },
  changePassword(payload: { current_password: string; new_password: string }) {
    return http.post<void>('/users/me/password', payload).then((r) => r.data);
  },

  // ---------- users ----------
  listUsers() { return http.get<User[]>('/users').then((r) => r.data); },
  createUser(payload: Partial<User> & { password: string }) {
    return http.post<User>('/users', payload).then((r) => r.data);
  },
  updateUser(id: number, payload: Partial<User>) {
    return http.patch<User>(`/users/${id}`, payload).then((r) => r.data);
  },
  deleteUser(id: number) { return http.delete<void>(`/users/${id}`).then((r) => r.data); },

  // ---------- providers ----------
  listProviders() { return http.get<Provider[]>('/providers').then((r) => r.data); },
  createProvider(payload: Partial<Provider>) {
    return http.post<Provider>('/providers', payload).then((r) => r.data);
  },
  updateProvider(id: number, payload: Partial<Provider>) {
    return http.patch<Provider>(`/providers/${id}`, payload).then((r) => r.data);
  },
  deleteProvider(id: number) { return http.delete<void>(`/providers/${id}`).then((r) => r.data); },

  // ---------- proxies ----------
  listProxies(params: Record<string, unknown> = {}) {
    return http.get<Proxy[]>('/proxies', { params }).then((r) => r.data);
  },
  createProxy(payload: any) { return http.post<Proxy>('/proxies', payload).then((r) => r.data); },
  bulkCreateProxies(payload: any) { return http.post<Proxy[]>('/proxies/bulk', payload).then((r) => r.data); },
  updateProxy(id: number, payload: any) { return http.patch<Proxy>(`/proxies/${id}`, payload).then((r) => r.data); },
  deleteProxy(id: number) { return http.delete<void>(`/proxies/${id}`).then((r) => r.data); },
  unlockProxy(id: number) { return http.post<Proxy>(`/proxies/${id}/unlock`).then((r) => r.data); },

  // ---------- groups ----------
  listGroups() { return http.get<ProxyGroup[]>('/groups').then((r) => r.data); },
  createGroup(payload: any) { return http.post<ProxyGroup>('/groups', payload).then((r) => r.data); },
  updateGroup(id: number, payload: any) { return http.patch<ProxyGroup>(`/groups/${id}`, payload).then((r) => r.data); },
  deleteGroup(id: number) { return http.delete<void>(`/groups/${id}`).then((r) => r.data); },

  // ---------- robots ----------
  listRobots() { return http.get<Robot[]>('/robots').then((r) => r.data); },
  createRobot(payload: any) { return http.post<Robot>('/robots', payload).then((r) => r.data); },
  updateRobot(id: number, payload: any) { return http.patch<Robot>(`/robots/${id}`, payload).then((r) => r.data); },
  rotateRobotKey(id: number) { return http.post<Robot>(`/robots/${id}/rotate-key`).then((r) => r.data); },
  deleteRobot(id: number) { return http.delete<void>(`/robots/${id}`).then((r) => r.data); },

  // ---------- domains ----------
  listDomains() { return http.get<Domain[]>('/domains').then((r) => r.data); },
  createDomain(payload: any) { return http.post<Domain>('/domains', payload).then((r) => r.data); },
  updateDomain(id: number, payload: any) { return http.patch<Domain>(`/domains/${id}`, payload).then((r) => r.data); },
  deleteDomain(id: number) { return http.delete<void>(`/domains/${id}`).then((r) => r.data); },

  // ---------- strategies ----------
  listStrategyKinds() { return http.get<StrategyKindInfo[]>('/strategies/kinds').then((r) => r.data); },
  previewStrategy(payload: { kind: string; parameters: Record<string, unknown> }) {
    return http.post<Record<string, unknown>>('/strategies/preview', payload).then((r) => r.data);
  },
  listStrategyConfigs() { return http.get<StrategyConfig[]>('/strategies').then((r) => r.data); },
  createStrategyConfig(payload: any) { return http.post<StrategyConfig>('/strategies', payload).then((r) => r.data); },
  updateStrategyConfig(id: number, payload: any) { return http.patch<StrategyConfig>(`/strategies/${id}`, payload).then((r) => r.data); },
  deleteStrategyConfig(id: number) { return http.delete<void>(`/strategies/${id}`).then((r) => r.data); },

  // ---------- logs & metrics ----------
  listLogs(params: Record<string, unknown> = {}) {
    return http.get<RequestLog[]>('/logs', { params }).then((r) => r.data);
  },
  metricsSummary(params: MetricsFilters = {}) {
    return http.get<MetricsSummary>('/metrics/summary', { params }).then((r) => r.data);
  },
  metricsTimeseries(params: MetricsFilters & { interval?: string } = {}) {
    return http.get<TimeseriesPoint[]>('/metrics/timeseries', { params }).then((r) => r.data);
  },
  metricsStatusCodes(params: MetricsFilters = {}) {
    return http.get<StatusCodeBucket[]>('/metrics/status-codes', { params }).then((r) => r.data);
  },
  topRobots(params: MetricsFilters & { limit?: number } = {}) {
    return http.get<TopItem[]>('/metrics/top/robots', { params }).then((r) => r.data);
  },
  topProxies(params: MetricsFilters & { limit?: number } = {}) {
    return http.get<TopItem[]>('/metrics/top/proxies', { params }).then((r) => r.data);
  },
  topHosts(params: MetricsFilters & { limit?: number } = {}) {
    return http.get<TopItem[]>('/metrics/top/hosts', { params }).then((r) => r.data);
  },
  metricsBreakdown(params: MetricsFilters & { dimension: string; limit?: number }) {
    return http.get<TopItem[]>('/metrics/breakdown', { params }).then((r) => r.data);
  },
};
