"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { RiskBadge } from "@/components/shared/risk-badge";
import { WorkflowStatusBadge } from "@/components/shared/status-badge";
import { DataTable, SortButton } from "@/components/tables/data-table";
import { Button } from "@/components/ui/button";
import { routes } from "@/constants/routes";
import { formatCurrency } from "@/lib/utils";
import type { Investigation } from "@/types/domain";

const columns: ColumnDef<Investigation>[] = [
  {
    accessorKey: "id",
    header: () => <SortButton label="Case" />,
    cell: ({ row }) => (
      <Link className="font-mono text-primary hover:underline" href={routes.caseWorkspace(row.original.id)}>
        {row.original.id}
      </Link>
    ),
  },
  {
    accessorKey: "vendor",
    header: "Vendor / category",
    cell: ({ row }) => (
      <div>
        <p className="font-medium text-foreground">{row.original.vendor}</p>
        <p className="text-xs text-muted-foreground">{row.original.category}</p>
      </div>
    ),
  },
  {
    accessorKey: "amount",
    header: () => <SortButton label="Amount" />,
    cell: ({ row }) => <span className="font-mono text-foreground">{formatCurrency(row.original.amount)}</span>,
  },
  {
    accessorKey: "risk",
    header: "Risk",
    cell: ({ row }) => <RiskBadge risk={row.original.risk} />,
  },
  {
    accessorKey: "confidence",
    header: "Confidence",
    cell: ({ row }) => <ConfidenceMeter value={row.original.confidence} className="min-w-32" />,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <WorkflowStatusBadge status={row.original.status} />,
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => (
      <Button asChild variant="ghost" size="sm">
        <Link href={routes.caseWorkspace(row.original.id)}>Open</Link>
      </Button>
    ),
  },
];

export function InvestigationsTable({ investigations }: { investigations: Investigation[] }) {
  return <DataTable columns={columns} data={investigations} emptyLabel="No investigations match this view." />;
}
