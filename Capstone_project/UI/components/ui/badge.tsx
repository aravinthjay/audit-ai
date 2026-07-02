import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "border-border bg-muted text-muted-foreground",
        primary: "border-primary-border bg-primary-soft text-primary",
        success: "border-success-border bg-success-soft text-success-foreground",
        warning: "border-warning-border bg-warning-soft text-warning-foreground",
        danger: "border-danger-border bg-danger-soft text-danger-foreground",
        info: "border-info-border bg-info-soft text-info-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export type BadgeProps = React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>;

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
