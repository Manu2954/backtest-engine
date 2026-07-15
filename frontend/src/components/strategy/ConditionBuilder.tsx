import { useStrategyBuilderStore } from "../../store/strategyBuilderStore";
import { ConditionRow } from "./ConditionRow";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

export function ConditionBuilder() {
  const entry = useStrategyBuilderStore((s) => s.entry);
  const exit = useStrategyBuilderStore((s) => s.exit);
  const setEntryLogic = useStrategyBuilderStore((s) => s.setEntryLogic);
  const setExitLogic = useStrategyBuilderStore((s) => s.setExitLogic);
  const addCondition = useStrategyBuilderStore((s) => s.addCondition);

  return (
    <div className="flex flex-col gap-6">
      {/* Entry Conditions */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Entry Conditions</CardTitle>
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Logic:</label>
              <Select
                value={entry.logic}
                onValueChange={(value) => setEntryLogic(value as "AND" | "OR")}
              >
                <SelectTrigger className="w-20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="AND">AND</SelectItem>
                  <SelectItem value="OR">OR</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {entry.conditions.length === 0 && (
            <div className="flex items-center gap-2 rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">
              <AlertCircle className="h-4 w-4" />
              No entry conditions. Add conditions to define when to enter a trade.
            </div>
          )}

          <div className="flex flex-col gap-2">
            {entry.conditions.map((condition, idx) => (
              <ConditionRow key={idx} condition={condition} index={idx} target="entry" />
            ))}
          </div>

          <Button variant="outline" size="sm" onClick={() => addCondition("entry")}>
            Add Entry Condition
          </Button>
        </CardContent>
      </Card>

      {/* Exit Conditions */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Exit Conditions</CardTitle>
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Logic:</label>
              <Select
                value={exit.logic}
                onValueChange={(value) => setExitLogic(value as "AND" | "OR")}
              >
                <SelectTrigger className="w-20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="AND">AND</SelectItem>
                  <SelectItem value="OR">OR</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {exit.conditions.length === 0 && (
            <div className="flex items-center gap-2 rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">
              <AlertCircle className="h-4 w-4" />
              No exit conditions. Add conditions to define when to exit a trade.
            </div>
          )}

          <div className="flex flex-col gap-2">
            {exit.conditions.map((condition, idx) => (
              <ConditionRow key={idx} condition={condition} index={idx} target="exit" />
            ))}
          </div>

          <Button variant="outline" size="sm" onClick={() => addCondition("exit")}>
            Add Exit Condition
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
