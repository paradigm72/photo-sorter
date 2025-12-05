// frontend/app/page.tsx
const API_BASE = process.env.NEXT_PUBLIC_API_BASE;

async function getStats() {
  const url = API_BASE ? `${API_BASE}/stats` : `/api/stats`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load stats");
  return res.json() as Promise<{ total: number; with_faces: number }>;
}

async function getPeople() {
  const url = API_BASE ? `${API_BASE}/people` : `/api/people`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) return [];
  return (await res.json()) as Array<{ id: number; path: string; face_count: number }>;
}

export default async function Page() {
  const stats = await getStats();
  const people = await getPeople();
  return (
    <div>
      <h2>Dashboard</h2>
      <p>Total photos: {stats.total}</p>
      <p>Photos with people: {stats.with_faces}</p>
      <form action={`/api/scan`} method="post">
        <button type="submit">Rescan Photos</button>
      </form>
      {/* people preview removed from Dashboard per UX request */}
    </div>
  );
}
