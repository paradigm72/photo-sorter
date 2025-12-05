// frontend/app/times/page.tsx
const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

type TimeBucket = {
  year: number;
  month: number;
  count: number;
};

async function getTimes(): Promise<TimeBucket[]> {
  const res = await fetch(`${API_BASE}/times`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load times");
  return res.json();
}

async function getPhotos(limit = 500) {
  const res = await fetch(`${API_BASE}/photos?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

function formatMonth(m: number) {
  return String(m).padStart(2, "0");
}

export default async function TimesPage() {
  const buckets = await getTimes();
  const photos = await getPhotos(1000);
  // group photos by year-month
  const groups: Record<string, Array<any>> = {};
  photos.forEach((p: any) => {
    const y = p.year || 0;
    const m = p.month || 0;
    const key = `${y}-${String(m).padStart(2, "0")}`;
    groups[key] = groups[key] || [];
    groups[key].push(p);
  });
  return (
    <div>
      <h2>Times</h2>
      {!buckets.length && <p>No dated photos yet.</p>}
      <div style={{ display: 'grid', gap: 12 }}>
        {buckets.map((b, idx) => {
          const key = `${b.year}-${String(b.month).padStart(2, "0")}`;
          const group = groups[key] || [];
          return (
            <div key={idx} style={{ border: '1px solid var(--border)', padding: 8, borderRadius: 8 }}>
              <h3 style={{ margin: '0 0 8px 0' }}>{b.year}-{formatMonth(b.month)} ({b.count})</h3>
              {group.length === 0 ? (
                <p style={{ margin: 0, color: 'var(--muted)' }}>No preview available</p>
              ) : (
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {group.slice(0, 6).map((p: any) => (
                    <img key={p.id} src={`/api/photo/${p.id}/image`} alt={`p-${p.id}`} style={{ width: 120, height: 90, objectFit: 'cover', borderRadius: 6 }} loading="lazy" />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
