import { Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { StatusBadge } from "@/components/shared/status-badge";
import type { AgentHealth } from "@/types/domain";

export function AgentHealthPanel({ agents }: { agents: AgentHealth[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Agent health</CardTitle>
        <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
      </CardHeader>
      <CardContent className="space-y-4">
        {agents.length > 0 ? (
          agents.map((agent) => (
            <div key={agent.label} className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-foreground">{agent.label}</span>
                <span className="ml-auto font-mono text-xs text-muted-foreground">{agent.latency}</span>
                <StatusBadge state={agent.state} />
              </div>
              <Progress value={agent.load} tone={agent.state === "running" ? "warning" : "success"} />
            </div>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">No live agent health endpoint is connected yet.</p>
        )}
      </CardContent>
    </Card>
  );
}
