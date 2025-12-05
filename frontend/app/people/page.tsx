// frontend/app/people/page.tsx
const API_BASE = process.env.NEXT_PUBLIC_API_BASE!;

type PersonPhoto = {
  id: number;
  path: string;
  face_count: number;
};

async function getPeoplePhotos(): Promise<PersonPhoto[]> {
  const res = await fetch(`${API_BASE}/people`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load people");
  return res.json();
}

export default async function PeoplePage() {
  const photos = await getPeoplePhotos();
  return (
    <div>
      <h2>People</h2>
      <p>Showing photos where faces were detected.</p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: "0.75rem",
        }}
      >
        {photos.map((p) => (
          <div
            key={p.id}
            style={{
              border: "1px solid var(--border)",
              padding: "0.25rem",
              borderRadius: "8px",
              overflow: "hidden",
              fontSize: "0.85rem",
            }}
          >
            <img
              src={`/api/photo/${p.id}/image`}
              alt={`photo-${p.id}`}
              style={{ width: "100%", height: 140, objectFit: "cover", display: "block", borderRadius: 6 }}
              loading="lazy"
            />
            <div style={{ marginTop: 6, fontSize: 12, color: "var(--muted)" }}>
              Faces: {p.face_count}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
