import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
};

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="relative flex animate-surface-in flex-col gap-4 border-b border-border pb-5 md:flex-row md:items-end md:justify-between">
      <span className="absolute bottom-[-1px] left-0 h-px w-36 bg-gradient-to-r from-primary to-info" aria-hidden="true" />
      <div className="min-w-0">
        {eyebrow ? (
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-primary">{eyebrow}</p>
        ) : null}
        <h1 className="mt-2 break-words text-xl font-semibold text-foreground md:text-2xl">{title}</h1>
        <p className="mt-2 max-w-3xl break-words text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
