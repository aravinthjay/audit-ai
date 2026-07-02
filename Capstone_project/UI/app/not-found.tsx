import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-6">
      <section className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-card">
        <p className="text-xs font-medium uppercase text-muted-foreground">404</p>
        <h1 className="mt-2 text-xl font-semibold">Page not found</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The workspace route does not exist or has moved.
        </p>
        <Button asChild className="mt-5">
          <Link href="/dashboard">Return to dashboard</Link>
        </Button>
      </section>
    </main>
  );
}
