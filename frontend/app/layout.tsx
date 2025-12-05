// frontend/app/layout.tsx
import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";
import ThemeToggle from "../components/ThemeToggle";

export const metadata = {
  title: "AI Photo Sorter",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        {/* Inline script to set initial theme quickly to avoid flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(() => {
              try {
                const k = 'theme-preference';
                const v = localStorage.getItem(k);
                if (v === 'light' || v === 'dark') {
                  document.documentElement.setAttribute('data-theme', v);
                } else {
                  document.documentElement.removeAttribute('data-theme');
                }
              } catch (e) {}
            })();`,
          }}
        />
        <header style={{ padding: "1rem", borderBottom: "1px solid #ccc", display: 'flex', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: 0 }}>AI Photo Sorter</h1>
            <nav style={{ marginTop: "0.5rem" }}>
              <Link href="/">Dashboard</Link>{" | "}
              <Link href="/people">People</Link>{" | "}
              <Link href="/places">Places</Link>{" | "}
              <Link href="/times">Times</Link>
            </nav>
          </div>
          <div className="header-right">
            <ThemeToggle />
          </div>
        </header>
        <main style={{ padding: "1rem" }}>{children}</main>
      </body>
    </html>
  );
}
