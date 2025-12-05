// frontend/app/page.tsx
const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

async function getStats() {
  const res = await fetch(`${API_BASE}/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load stats");
  return res.json() as Promise<{ total: number; with_faces: number }>;
}

export default async function Page() {
  const stats = await getStats();
  return (
    <div>
      <h2>Dashboard</h2>
      <p>Total photos: {stats.total}</p>
      <p>Photos with people: {stats.with_faces}</p>
      <form action={`${API_BASE}/scan`} method="post">
        <button type="submit">Rescan Photos</button>
      </form>
    </div>
  );
}
