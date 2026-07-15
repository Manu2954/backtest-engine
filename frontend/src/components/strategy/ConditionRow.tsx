import { OPERATORS, OPERAND_TYPES, OHLCV_COLUMNS, isUnaryOperator } from "../../lib/constants";
import { useStrategyBuilderStore } from "../../store/strategyBuilderStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Trash2 } from "lucide-react";
import type { ConditionInput, OperandType, OperatorType } from "../../types";

interface ConditionRowProps {
  condition: ConditionInput;
  index: number;
  target: "entry" | "exit";
}

export function ConditionRow({ condition, index, target }: ConditionRowProps) {
  const updateCondition = useStrategyBuilderStore((s) => s.updateCondition);
  const removeCondition = useStrategyBuilderStore((s) => s.removeCondition);
  const indicatorAliases = useStrategyBuilderStore((s) => s.getIndicatorAliases());

  const isUnary = isUnaryOperator(condition.operator);

  const handleChange = (patch: Partial<ConditionInput>) => {
    updateCondition(target, index, patch);
  };

  const getValueOptions = (type: OperandType): string[] => {
    if (type === "INDICATOR") return indicatorAliases;
    if (type === "OHLCV") return [...OHLCV_COLUMNS];
    return [];
  };

  const renderOperandValue = (
    side: "left" | "right",
    type: OperandType,
    value: string
  ) => {
    const options = getValueOptions(type);
    const isInput = type === "SCALAR" || type === "LOOKBACK";

    if (isInput) {
      return (
        <Input
          value={value}
          placeholder={type === "LOOKBACK" ? "column:-offset (e.g., close:-10)" : "Enter value"}
          onChange={(e) =>
            handleChange({
              [`${side}_operand_value`]: e.target.value,
            })
          }
          className="min-w-[120px]"
        />
      );
    }

    return (
      <Select
        value={value || options[0] || ""}
        onValueChange={(newValue) =>
          handleChange({
            [`${side}_operand_value`]: newValue,
          })
        }
      >
        <SelectTrigger className="min-w-[120px]">
          <SelectValue placeholder="Select..." />
        </SelectTrigger>
        <SelectContent>
          {options.length === 0 && (
            <SelectItem value="" disabled>-- No options --</SelectItem>
          )}
          {options.map((opt) => (
            <SelectItem key={opt} value={opt}>
              {opt}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  };

  return (
    <Card className="p-3">
      <div className="flex flex-wrap items-end gap-2">
        {/* Left operand type */}
        <div className="flex-shrink-0">
          <Label className="text-xs text-muted-foreground">Left Type</Label>
          <Select
            value={condition.left_operand_type}
            onValueChange={(value) => handleChange({ left_operand_type: value as OperandType })}
          >
            <SelectTrigger className="w-[100px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {OPERAND_TYPES.map((t) => (
                <SelectItem key={t.value} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Left operand value */}
        <div className="min-w-[100px] flex-1">
          <Label className="text-xs text-muted-foreground">Left Value</Label>
          {renderOperandValue("left", condition.left_operand_type, condition.left_operand_value)}
        </div>

        {/* Operator */}
        <div className="flex-shrink-0">
          <Label className="text-xs text-muted-foreground">Operator</Label>
          <Select
            value={condition.operator}
            onValueChange={(value) => handleChange({ operator: value as OperatorType })}
          >
            <SelectTrigger className="w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {OPERATORS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Right operand (hidden for unary operators) */}
        {!isUnary && (
          <>
            <div className="flex-shrink-0">
              <Label className="text-xs text-muted-foreground">Right Type</Label>
              <Select
                value={condition.right_operand_type}
                onValueChange={(value) => handleChange({ right_operand_type: value as OperandType })}
              >
                <SelectTrigger className="w-[100px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OPERAND_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="min-w-[100px] flex-1">
              <Label className="text-xs text-muted-foreground">Right Value</Label>
              {renderOperandValue("right", condition.right_operand_type, condition.right_operand_value)}
            </div>
          </>
        )}

        {/* Delete button */}
        <Button
          variant="ghost"
          size="icon"
          className="self-end text-destructive hover:text-destructive hover:bg-destructive/10"
          onClick={() => removeCondition(target, index)}
          aria-label="Delete condition"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </Card>
  );
}
