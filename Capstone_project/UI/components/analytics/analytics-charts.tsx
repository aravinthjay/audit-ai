"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AgentAccuracy, AnalyticsPoint } from "@/types/domain";

type AnalyticsChartsProps = {
  trend: AnalyticsPoint[];
  accuracy: AgentAccuracy[];
};

export function AnalyticsCharts({ trend, accuracy }: AnalyticsChartsProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Confidence and verifier grounding</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
                <XAxis dataKey="week" stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
                <YAxis
                  stroke="hsl(var(--muted-foreground))"
                  tickLine={false}
                  axisLine={false}
                  domain={[0.65, 1]}
                  tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                  formatter={(value: number) => `${Math.round(value * 100)}%`}
                />
                <Line type="monotone" dataKey="confidence" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                <Line
                  type="monotone"
                  dataKey="verifierRate"
                  stroke="hsl(var(--success))"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Agent accuracy</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={accuracy} layout="vertical" margin={{ top: 8, right: 24, left: 18, bottom: 8 }}>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  domain={[0.75, 1]}
                  stroke="hsl(var(--muted-foreground))"
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
                />
                <YAxis
                  dataKey="agent"
                  type="category"
                  width={86}
                  stroke="hsl(var(--muted-foreground))"
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                  formatter={(value: number) => `${Math.round(value * 100)}%`}
                />
                <Bar dataKey="accuracy" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
