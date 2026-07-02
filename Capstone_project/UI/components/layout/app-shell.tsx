"use client";

import { Menu, Search, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { commandItems, navigationSections } from "@/constants/navigation";
import { routes } from "@/constants/routes";
import { cn } from "@/lib/utils";
import { useUiState } from "@/store/ui-state";

function getActiveHref(pathname: string) {
  if (pathname.startsWith(`${routes.investigations}/`)) {
    return routes.workspace;
  }

  const hrefs = navigationSections.flatMap((section) => section.items.map((item) => item.href));
  const matches = hrefs.filter((href) => pathname === href || pathname.startsWith(`${href}/`)).sort((a, b) => b.length - a.length);

  return matches[0];
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const activeHref = getActiveHref(pathname);

  return (
    <div className="flex h-full flex-col">
      <Link
        href="/dashboard"
        className="flex items-center gap-3 border-b border-border px-4 py-4 text-foreground"
        onClick={onNavigate}
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary-border bg-primary-soft text-primary">
          <ShieldCheck className="h-5 w-5" aria-hidden="true" />
        </span>
        <span className="min-w-0">
          <span className="block truncate text-sm font-semibold">Skepticism Engine</span>
          <span className="block truncate text-xs text-muted-foreground">Enterprise audit AI</span>
        </span>
      </Link>

      <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Primary navigation">
        <div className="space-y-5">
          {navigationSections.map((section) => (
            <section key={section.label} aria-labelledby={`nav-${section.label}`}>
              <h2
                id={`nav-${section.label}`}
                className="px-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground"
              >
                {section.label}
              </h2>
              <div className="mt-2 space-y-1">
                {section.items.map((item) => {
                  const active = activeHref === item.href;
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={onNavigate}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex items-center gap-3 rounded-md px-2.5 py-2 text-sm transition-colors",
                        active
                          ? "bg-primary-soft text-primary"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      </nav>

      <div className="border-t border-border p-3">
        <div className="rounded-lg border border-border bg-background/60 p-3">
          <p className="text-xs font-medium text-foreground">Platform health</p>
          <div className="mt-3 space-y-2">
            <p className="text-xs text-muted-foreground">Live service checks are not exposed by the UI API yet.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function AppHeader() {
  const { setCommandOpen, setSidebarOpen } = useUiState();

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-card/92 shadow-sm backdrop-blur">
      <div className="flex h-14 items-center gap-3 px-4 lg:px-6">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label="Open navigation"
          onClick={() => setSidebarOpen(true)}
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </Button>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">Skeptic Engine</p>
          <p className="truncate text-xs text-muted-foreground">Live backend workspace</p>
        </div>

        <Button
          variant="secondary"
          className="hidden min-w-64 justify-start text-muted-foreground sm:flex"
          onClick={() => setCommandOpen(true)}
        >
          <Search className="h-4 w-4" aria-hidden="true" />
          Search cases, evidence, and reports
        </Button>
        <Button variant="ghost" size="icon" className="sm:hidden" aria-label="Search" onClick={() => setCommandOpen(true)}>
          <Search className="h-5 w-5" aria-hidden="true" />
        </Button>

        <div className="hidden items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground md:flex">
          <span className="h-2 w-2 rounded-full bg-success" aria-hidden="true" />
          Immutable log online
        </div>
      </div>
    </header>
  );
}

function CommandOverlay() {
  const { commandOpen, setCommandOpen } = useUiState();

  if (!commandOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 animate-in fade-in-0 bg-black/60 p-4 backdrop-blur-sm" role="presentation">
      <div
        className="mx-auto mt-16 w-full max-w-xl animate-in fade-in-0 zoom-in-95 overflow-hidden rounded-lg border border-border bg-card shadow-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Search navigation"
      >
        <div className="flex items-center gap-3 border-b border-border px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <span className="flex-1 text-sm text-muted-foreground">Jump to a workspace area</span>
          <Button variant="ghost" size="icon" aria-label="Close search" onClick={() => setCommandOpen(false)}>
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
        <div className="max-h-96 overflow-y-auto p-2">
          {commandItems.map((item) => {
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
                onClick={() => setCommandOpen(false)}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span className="flex-1">{item.label}</span>
                <span className="text-xs text-muted-foreground">{item.section}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { sidebarOpen, setSidebarOpen } = useUiState();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 border-r border-border bg-card shadow-sm lg:block">
        <SidebarContent />
      </aside>

      {sidebarOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            className="absolute inset-0 bg-black/60"
            aria-label="Close navigation"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative h-full w-60 border-r border-border bg-card shadow-panel">
            <SidebarContent onNavigate={() => setSidebarOpen(false)} />
          </aside>
        </div>
      ) : null}

      <div className="lg:pl-60">
        <AppHeader />
        <main className="mx-auto w-full max-w-7xl px-4 py-6 lg:px-6">{children}</main>
      </div>
      <CommandOverlay />
    </div>
  );
}
