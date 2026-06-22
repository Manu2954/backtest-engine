import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { OPERATORS, OPERAND_TYPES, OHLCV_COLUMNS } from "@/lib/constants";
import type { Condition, Indicator } from "@/types";

interface ConditionBuilderProps {
  condition: Condition;
  indicators: Indicator[];
  onChange: (condition: Partial<Condition>) => void;
  onRemove: () => void;
  canRemove?: boolean;
}

export function ConditionBuilder({
  condition,
  indicators,
  onChange,
  onRemove,
  canRemove = true,
}: ConditionBuilderProps) {
  // Get all available indicator outputs
  const indicatorOutputs = indicators.flatMap((ind) => {
    // Simple outputs
    const outputs: string[] = [ind.alias];

    // Multi-output indicators
    const type = ind.indicator_type.toUpperCase();
    if (type === "MACD") {
      return [`${ind.alias}_macd`, `${ind.alias}_signal`, `${ind.alias}_hist`];
    }
    if (type === "BB" || type === "BBANDS" || type === "BOLLINGER") {
      return [`${ind.alias}_upper`, `${ind.alias}_mid`, `${ind.alias}_lower`];
    }
    if (type === "STOCH" || type === "STOCHASTIC") {
      return [`${ind.alias}_k`, `${ind.alias}_d`];
    }
    if (type === "ADX") {
      return [ind.alias, `${ind.alias}_dmp`, `${ind.alias}_dmn`];
    }
    if (type === "DONCHIAN" || type === "DC") {
      return [`${ind.alias}_upper`, `${ind.alias}_lower`, `${ind.alias}_mid`];
    }
    if (type === "SUPERTREND") {
      return [ind.alias, `${ind.alias}_trend`, `${ind.alias}_long`, `${ind.alias}_short`];
    }
    if (type === "HEIKINASHI" || type === "HA") {
      return [`${ind.alias}_open`, `${ind.alias}_high`, `${ind.alias}_low`, `${ind.alias}_close`];
    }

    return outputs;
  });

  const renderOperandSelect = (
    type: string,
    value: string,
    onTypeChange: (t: string) => void,
    onValueChange: (v: string) => void
  ) => {
    return (
      <div className="flex gap-2 flex-1">
        <Select value={type} onValueChange={onTypeChange}>
          <SelectTrigger className="w-[130px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {OPERAND_TYPES.map((op) => (
              <SelectItem key={op.value} value={op.value}>
                {op.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {type === "INDICATOR" && (
          <Select value={value} onValueChange={onValueChange}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Select indicator" />
            </SelectTrigger>
            <SelectContent>
              {indicatorOutputs.map((output) => (
                <SelectItem key={output} value={output}>
                  {output}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {type === "OHLCV" && (
          <Select value={value} onValueChange={onValueChange}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Select column" />
            </SelectTrigger>
            <SelectContent>
              {OHLCV_COLUMNS.map((col) => (
                <SelectItem key={col} value={col}>
                  {col}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {type === "SCALAR" && (
          <Input
            type="number"
            value={value}
            onChange={(e) => onValueChange(e.target.value)}
            placeholder="Value"
            className="flex-1"
          />
        )}

        {type === "LOOKBACK" && (
          <Input
            value={value}
            onChange={(e) => onValueChange(e.target.value)}
            placeholder="column:-offset (e.g., close:-10)"
            className="flex-1"
          />
        )}
      </div>
    );
  };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Left operand */}
      {renderOperandSelect(
        condition.left_operand_type,
        condition.left_operand_value,
        (t) => onChange({ left_operand_type: t }),
        (v) => onChange({ left_operand_value: v })
      )}

      {/* Operator */}
      <Select
        value={condition.operator}
        onValueChange={(v) => onChange({ operator: v })}
      >
        <SelectTrigger className="w-[140px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {OPERATORS.map((op) => (
            <SelectItem key={op.value} value={op.value}>
              {op.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Right operand */}
      {renderOperandSelect(
        condition.right_operand_type,
        condition.right_operand_value,
        (t) => onChange({ right_operand_type: t }),
        (v) => onChange({ right_operand_value: v })
      )}

      {/* Remove button */}
      {canRemove && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onRemove}
          className="text-destructive hover:text-destructive shrink-0"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
