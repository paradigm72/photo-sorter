"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "theme-preference"; // values: 'system' | 'light' | 'dark'

export default function ThemeToggle() {
  const [theme, setTheme] = useState<"system" | "light" | "dark">("system");

  useEffect(() => {
    try {
      const v = localStorage.getItem(STORAGE_KEY) as
        | "system"
        | "light"
        | "dark"
        | null;
      if (v === "light" || v === "dark" || v === "system") {
        setTheme(v);
      }
    } catch (e) {}
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {}
  }, [theme]);

  const btnClass = (value: string) =>
    `theme-btn${theme === value ? " theme-btn-active" : ""}`;

  return (
    <div className="theme-toggle" role="toolbar" aria-label="Theme">
      <button
        className={btnClass("system")}
        onClick={() => setTheme("system")}
        title="Follow system theme"
        aria-pressed={theme === "system"}
      >
        {/* computer / monitor icon */}
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M3 4c0-1.1.9-2 2-2h14a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-6l1 2h2v1H6v-1h2l1-2H5a2 2 0 0 1-2-2V4zm2 0v11h14V4H5z" />
        </svg>
        <span className="sr-only">System</span>
      </button>
      <button
        className={btnClass("light")}
        onClick={() => setTheme("light")}
        title="Light theme"
        aria-pressed={theme === "light"}
      >
        {/* sun icon */}
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M6.76 4.84l-1.8-1.79L3.17 4.84l1.79 1.79 1.8-1.79zM1 13h3v-2H1v2zm10-9h2V1h-2v3zm7.03 2.05l1.79-1.8-1.79-1.79-1.8 1.79 1.8 1.8zM17 13h3v-2h-3v2zM11 20h2v-3h-2v3zm6.24-2.76l1.79 1.8 1.79-1.8-1.79-1.79-1.79 1.79zM6.76 19.16l-1.79 1.79 1.79 1.79 1.8-1.79-1.8-1.79zM12 7a5 5 0 100 10 5 5 0 000-10z" />
        </svg>
        <span className="sr-only">Light</span>
      </button>
      <button
        className={btnClass("dark")}
        onClick={() => setTheme("dark")}
        title="Dark theme"
        aria-pressed={theme === "dark"}
      >
        {/* moon icon */}
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
        </svg>
        <span className="sr-only">Dark</span>
      </button>
    </div>
  );
}
