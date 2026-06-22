import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConditionBuilder } from "./ConditionBuilder";
import type { Condition, ConditionGroup as ConditionGroupType, Indicator } from "@/types";

interface ConditionGroupProps {
  title: string;
  description?: string;
  group: ConditionGroupType;
  indicators: Indicator[];
  onLogicChange: (logic: "AND" | "OR") => void;
  onConditionChange: (index: number, condition: Partial<Condition>) => void;
  onConditionAdd: () => void;
  onConditionRemove: (index: number) => void;
}

export function ConditionGroup({
  title,
  description,
  group,
  indicators,
  onLogicChange,
  onConditionChange,
  onConditionAdd,
  onConditionRemove,
}: ConditionGroupProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">{title}</CardTitle>
            {description && (
              <p className="text-sm text-muted-foreground mt-1">{description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-sm">Logic:</Label>
            <Select value={group.logic} onValueChange={(v) => onLogicChange(v as "AND" | "OR")}>
              <SelectTrigger className="w-[80px]">
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
      <CardContent className="space-y-4">
        {group.conditions.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground">
            No conditions. Add one to get started.
          </div>
        ) : (
          <div className="space-y-3">
            {group.conditions.map((condition, index) => (
              <div key={index}>
                {index > 0 && (
                  <div className="text-center text-sm text-muted-foreground py-1">
                    {group.logic}
                  </div>
                )}
                <ConditionBuilder
                  condition={condition}
                  indicators={indicators}
                  onChange={(c) => onConditionChange(index, c)}
                  onRemove={() => onConditionRemove(index)}
                  canRemove={group.conditions.length > 1}
                />
              </div>
            ))}
          </div>
        )}

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onConditionAdd}
          className="w-full"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Condition
        </Button>
      </CardContent>
    </Card>
  );
}
