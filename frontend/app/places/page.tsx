// frontend/app/places/page.tsx
const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

type PlaceGroup = {
  place: string;
  count: number;
};

async function getPlaces(): Promise<PlaceGroup[]> {
  const res = await fetch(`${API_BASE}/places`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load places");
  return res.json();
}

export default async function PlacesPage() {
  const places = await getPlaces();
  return (
    <div>
      <h2>Places</h2>
      {!places.length && <p>No place data yet.</p>}
      <ul>
        {places.map((p) => (
          <li key={p.place}>
            {p.place} ({p.count})
          </li>
        ))}
      </ul>
    </div>
  );
}
