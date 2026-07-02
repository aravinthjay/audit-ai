import * as React from "react";
import { cn } from "@/lib/utils";

type ProgressProps = React.ComponentProps<"div"> & {
  value: number;
  tone?: "primary" | "success" | "warning" | "danger" | "info";
};

const toneClass: Record<NonNullable<ProgressProps["tone"]>, string> = {
  primary: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
};

const widthClasses = [
  "w-0",
  "w-[5%]",
  "w-[10%]",
  "w-[15%]",
  "w-[20%]",
  "w-[25%]",
  "w-[30%]",
  "w-[35%]",
  "w-[40%]",
  "w-[45%]",
  "w-[50%]",
  "w-[55%]",
  "w-[60%]",
  "w-[65%]",
  "w-[70%]",
  "w-[75%]",
  "w-[80%]",
  "w-[85%]",
  "w-[90%]",
  "w-[95%]",
  "w-full",
] as const;

function progressWidthClass(value: number) {
  const bucket = Math.min(Math.max(Math.round(value * 20), 0), 20);

  return widthClasses[bucket];
}

export function Progress({ className, value, tone = "primary", ...props }: ProgressProps) {
  return (
    <div
      className={cn("h-2 overflow-hidden rounded-full bg-muted", className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(value * 100)}
      {...props}
    >
      <div className={cn("h-full rounded-full", toneClass[tone], progressWidthClass(value))} />
    </div>
  );
}
