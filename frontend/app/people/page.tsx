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
      <p>Showing photos where faces were detected (clustering can come later).</p>
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
              border: "1px solid #ddd",
              padding: "0.5rem",
              borderRadius: "8px",
              overflow: "hidden",
              fontSize: "0.85rem",
            }}
          >
            <div style={{ marginBottom: "0.25rem" }}>
              Faces: {p.face_count} <br />
              <span style={{ wordBreak: "break-all" }}>{p.path}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
