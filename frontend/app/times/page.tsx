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

function formatMonth(m: number) {
  return String(m).padStart(2, "0");
}

export default async function TimesPage() {
  const buckets = await getTimes();
  return (
    <div>
      <h2>Times</h2>
      {!buckets.length && <p>No dated photos yet.</p>}
      <ul>
        {buckets.map((b, idx) => (
          <li key={idx}>
            {b.year}-{formatMonth(b.month)} ({b.count})
          </li>
        ))}
      </ul>
    </div>
  );
}
