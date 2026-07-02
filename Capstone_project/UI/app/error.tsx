"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-6">
      <section className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-card">
        <p className="text-xs font-medium uppercase text-danger-foreground">Runtime error</p>
        <h1 className="mt-2 text-xl font-semibold">The workspace could not render</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Retry the screen. If it repeats, inspect the service response or component boundary.
        </p>
        <Button className="mt-5" onClick={reset}>
          Try again
        </Button>
      </section>
    </main>
  );
}
