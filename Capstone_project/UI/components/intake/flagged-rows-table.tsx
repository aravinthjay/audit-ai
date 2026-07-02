import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { routes } from "@/constants/routes";
import type { FlaggedRow } from "@/types/domain";

export function FlaggedRowsTable({ rows }: { rows: FlaggedRow[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Flagged rows &rarr; cases</CardTitle>
        <Link
          href={routes.investigations}
          className="inline-flex items-center gap-1 text-xs font-medium text-primary"
        >
          Open queue <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
                <th scope="col" className="px-4 py-2 font-medium">
                  Txn
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Vendor / account
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Amount
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Rules fired
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.txnId} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-mono text-muted-foreground">{row.txnId}</td>
                  <td className="px-4 py-3">
                    <span className="text-foreground">{row.vendor}</span>{" "}
                    <span className="text-muted-foreground">&middot; {row.account}</span>
                  </td>
                  <td className="px-4 py-3 font-mono">{row.amount}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {row.rules.map((rule) => (
                        <Badge key={rule} variant="default">
                          {rule}
                        </Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
