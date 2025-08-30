export async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = (typeof localStorage!=='undefined') ? localStorage.getItem('authToken') : null
  const headers: any = { 'Content-Type': 'application/json', ...(opts.headers||{}) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const base = (import.meta as any).env?.VITE_API_BASE || ''
  const url = (base && path.startsWith('/api')) ? `${base}${path}` : path
  const res = await fetch(url, { ...opts, headers })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<T>
}

export type LineupResp = { starters: any[], bench: any[], rationale: Record<string,string> }

export async function ingestAndBlend(week: number): Promise<{ok:boolean, counts:any, blended:number}> {
  return api(`/api/projections/ingest-blend?week=${week}`, { method: 'POST' })
}

export async function importSchedule(week: number, csv: string): Promise<{ok:boolean, imported:number}> {
  return api(`/api/admin/schedule/import?week=${week}`, { method: 'POST', body: JSON.stringify({ csv }) })
}

export async function updateWeather(week: number): Promise<{ok:boolean, updated_games:number}> {
  return api(`/api/admin/weather/update?week=${week}`, { method: 'POST' })
}

export async function getSettings(): Promise<{data:any}> {
  return api('/api/settings')
}

export async function saveSettings(data:any): Promise<{ok:boolean}> {
  return api('/api/settings', { method:'POST', body: JSON.stringify({ data }) })
}

export async function login(email: string, password: string): Promise<{ok:boolean, token:string}> {
  return api('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
}

export async function register(email: string, password: string): Promise<{ok:boolean, token:string}> {
  return api('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) })
}

export async function getMyRoster(): Promise<{roster:any[]}> {
  return api('/api/roster/my')
}

export async function getMyNews(): Promise<{items:any[]}> {
  return api('/api/news/my-players')
}

export async function getStandings(): Promise<{table:any[], source?:string}> {
  return api('/api/standings')
}

export async function getDashboardCards(): Promise<{injuries:any[], byes:any[], weather:any[], late_swap:any[], waivers:any[], trade:any[]}> {
  return api('/api/dashboard/cards')
}
