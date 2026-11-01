export interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface Assignment {
  id: number;
  course: string;
  title: string;
  open_at: string | null;
  due_at: string | null;
  status: string | null;
  status_label: string | null;
  description_text: string | null;
  url: string | null;
  attachments: unknown[] | null;
}

export interface Notification {
  id: number;
  notif_id: number | null;
  event: string;
  category: string;
  title: string | null;
  site_id: string | null;
  site_title: string | null;
  from_user: string | null;
  from_display_name: string | null;
  url: string | null;
  ref: string | null;
  event_date: string | null;
  formatted_event_date: string | null;
  body: string | null;
  body_text: string | null;
  read: boolean;
  first_seen_at: string;
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(config: ApiConfig, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${config.baseUrl}${path}`, {
    ...init,
    headers: {
      'X-API-Key': config.apiKey,
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(body || `HTTP ${res.status}`, res.status);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export function fetchMe(config: ApiConfig): Promise<User> {
  return request<User>(config, '/api/me');
}

export function fetchAssignments(config: ApiConfig, userId: number): Promise<Assignment[]> {
  return request<Assignment[]>(config, `/api/users/${userId}/assignments`);
}

export function fetchNotifications(config: ApiConfig, userId: number): Promise<Notification[]> {
  return request<Notification[]>(config, `/api/users/${userId}/notifications`);
}
