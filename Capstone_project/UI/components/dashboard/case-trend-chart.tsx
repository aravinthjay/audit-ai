"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsPoint } from "@/types/domain";

export function CaseTrendChart({ trend }: { trend: AnalyticsPoint[] }) {
  const chartData = trend.map((point, index) => ({
    ...point,
    cases: 72 + index * 9,
    highRisk: 9 + index,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Case trend</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 18, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="casesGradient" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.22} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
              <XAxis dataKey="week" stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
              <YAxis stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} width={34} />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  color: "hsl(var(--foreground))",
                }}
              />
              <Area
                type="monotone"
                dataKey="cases"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                fill="url(#casesGradient)"
              />
              <Area type="monotone" dataKey="highRisk" stroke="hsl(var(--danger))" strokeWidth={2} fill="transparent" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
