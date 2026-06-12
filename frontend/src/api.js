const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchDashboard() {
  const res = await fetch(`${BASE_URL}/dashboard`);
  if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchLogs() {
  const res = await fetch(`${BASE_URL}/logs`);
  if (!res.ok) throw new Error(`Logs fetch failed: ${res.status}`);
  return res.json();
}
