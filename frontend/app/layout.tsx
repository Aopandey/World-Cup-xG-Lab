import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "World Cup xG Lab",
  description: "Football analytics dashboard for historical xG, squad coverage, and recent player context."
};

const navItems = [
  { href: "/", label: "Teams" },
  { href: "/players", label: "Players" },
  { href: "/model", label: "Model" },
  { href: "/coverage", label: "Coverage" }
];

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-pitch-900 text-slate-100 antialiased">
        <div className="border-b border-white/10 bg-pitch-900/90 backdrop-blur">
          <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
            <Link href="/" className="text-lg font-black tracking-tight text-white">
              World Cup xG Lab
            </Link>
            <div className="flex gap-2">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-300 transition hover:bg-white/[0.06] hover:text-white"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </nav>
        </div>
        <main className="mx-auto max-w-7xl px-5 py-8 md:py-10">{children}</main>
        <footer className="mx-auto max-w-7xl px-5 pb-8 pt-4 text-sm leading-6 text-slate-500">
          StatsBomb powers the historical xG model and shot-location views. FBref adds recent aggregate player context.
          Understat adds club xG context. DataMB adds 25/26 percentile profiles. This dashboard is not a guaranteed
          2026 World Cup prediction model.
        </footer>
      </body>
    </html>
  );
}
