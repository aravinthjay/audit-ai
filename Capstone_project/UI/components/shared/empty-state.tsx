import type { LucideIcon } from "lucide-react";
import { FileSearch } from "lucide-react";
import { Button } from "@/components/ui/button";

type EmptyStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  icon?: LucideIcon;
};

export function EmptyState({ title, description, actionLabel, icon: Icon = FileSearch }: EmptyStateProps) {
  return (
    <section className="animate-surface-in rounded-lg border border-dashed border-border bg-gradient-to-b from-card to-muted/40 p-8 text-center shadow-card">
      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg border border-primary-border bg-primary-soft text-primary">
        <Icon className="h-6 w-6" aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-base font-semibold text-foreground">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
      {actionLabel ? (
        <Button className="mt-5" variant="secondary">
          {actionLabel}
        </Button>
      ) : null}
    </section>
  );
}
