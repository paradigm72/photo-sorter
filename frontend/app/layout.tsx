// frontend/app/layout.tsx
import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata = {
  title: "AI Photo Sorter",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header style={{ padding: "1rem", borderBottom: "1px solid #ccc" }}>
          <h1>AI Photo Sorter</h1>
          <nav style={{ marginTop: "0.5rem" }}>
            <Link href="/">Dashboard</Link>{" | "}
            <Link href="/people">People</Link>{" | "}
            <Link href="/places">Places</Link>{" | "}
            <Link href="/times">Times</Link>
          </nav>
        </header>
        <main style={{ padding: "1rem" }}>{children}</main>
      </body>
    </html>
  );
}
