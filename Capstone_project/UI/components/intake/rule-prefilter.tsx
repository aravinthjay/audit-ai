import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { IntakeRuleStat } from "@/types/domain";

export function RulePrefilter({ rules }: { rules: IntakeRuleStat[] }) {
  const max = Math.max(1, ...rules.map((rule) => rule.count));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Rule pre-filter</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">
          Rows tripping each deterministic rule (a row may trip several).
        </p>
        {rules.map((rule) => (
          <div key={rule.rule} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{rule.rule}</span>
              <span className="font-mono text-foreground">{rule.count}</span>
            </div>
            <Progress value={rule.count / max} tone={rule.tone} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
