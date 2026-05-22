export type UserRole = 'admin' | 'operator' | 'viewer';

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Provider {
  id: number;
  name: string;
  website: string | null;
  contact_email: string | null;
  notes: string | null;
  proxy_count: number;
  created_at: string;
}

export type ProxyProtocol = 'http' | 'https' | 'socks4' | 'socks5';

export interface Proxy {
  id: number;
  host: string;
  port: number;
  protocol: ProxyProtocol;
  username: string | null;
  is_active: boolean;
  expires_at: string | null;
  extra_metadata: Record<string, unknown> | null;
  last_used: string | null;
  success_count: number;
  failure_count: number;
  avg_response_time_ms: number;
  is_in_use: boolean;
  created_at: string;
  group_ids: number[];
  provider_id: number | null;
  provider_name: string | null;
  success_rate: number;
}

export interface ProxyGroup {
  id: number;
  name: string;
  description: string | null;
  default_strategy_id: number | null;
  created_at: string;
  proxy_count: number;
  robot_count: number;
}

export interface Robot {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  default_lease_minutes: number;
  created_at: string;
  group_ids: number[];
  api_key_prefix: string;
  api_key?: string;
}

export interface Domain {
  id: number;
  hostname: string;
  notes: string | null;
  is_blocked: boolean;
  rate_limit_per_minute: number | null;
  created_at: string;
}

export type StrategyKind = 'round_robin' | 'random' | 'bayesian_beta' | 'exponential_backoff';

export interface StrategyParameterSpec {
  name: string;
  type: string;
  default: unknown;
  min: number | null;
  max: number | null;
  description: string;
}

export interface StrategyKindInfo {
  kind: StrategyKind;
  label: string;
  description: string;
  parameters: StrategyParameterSpec[];
}

export interface StrategyConfig {
  id: number;
  name: string;
  description: string | null;
  kind: StrategyKind;
  parameters: Record<string, unknown>;
  created_at: string;
}

export interface RequestLog {
  id: number;
  proxy_id: number;
  group_id: number | null;
  robot_id: number | null;
  robot_name: string;
  target_url: string;
  target_host: string | null;
  strategy_id: number | null;
  strategy_kind: string | null;
  status_code: number | null;
  success: boolean;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
}

export interface MetricsSummary {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  average_duration_ms: number;
  active_proxies: number;
  active_robots: number;
}

export interface TimeseriesPoint {
  bucket: string;
  total: number;
  success: number;
  failure: number;
  success_rate: number;
}

export interface StatusCodeBucket {
  status_code: number | null;
  count: number;
}

export interface TopItem {
  key: string;
  label: string | null;
  total: number;
  success: number;
  failure: number;
  success_rate: number;
  avg_duration_ms: number;
}

export type BreakdownDimension = 'strategy' | 'robot' | 'provider' | 'group' | 'host' | 'proxy';

export interface MetricsFilters {
  robot_id?: number | null;
  group_id?: number | null;
  proxy_id?: number | null;
  target_host?: string | null;
  strategy_id?: number | null;
  strategy_kind?: string | null;
  since?: string | null;
  until?: string | null;
}
