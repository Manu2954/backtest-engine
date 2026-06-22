import { Trash2, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { INDICATOR_CONFIGS, type IndicatorType } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { Indicator } from "@/types";

interface IndicatorCardProps {
  indicator: Indicator;
  index: number;
  onChange: (indicator: Partial<Indicator>) => void;
  onRemove: () => void;
}

export function IndicatorCard({
  indicator,
  index,
  onChange,
  onRemove,
}: IndicatorCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const config = INDICATOR_CONFIGS[indicator.indicator_type as IndicatorType];

  const handleTypeChange = (type: string) => {
    const newConfig = INDICATOR_CONFIGS[type as IndicatorType];
    const defaultParams: Record<string, number | string> = {};

    newConfig.params.forEach((param) => {
      defaultParams[param.key] = param.default;
    });

    onChange({
      indicator_type: type,
      params: defaultParams,
    });
  };

  const handleParamChange = (key: string, value: string | number) => {
    onChange({
      params: {
        ...indicator.params,
        [key]: value,
      },
    });
  };

  const outputs = config?.outputs(indicator.alias) || [];

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-muted-foreground">
              #{index + 1}
            </span>
            <span className="font-semibold">{indicator.alias}</span>
            <span className="text-sm text-muted-foreground">
              ({config?.name || indicator.indicator_type})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onRemove}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className={cn("space-y-4", !isExpanded && "hidden")}>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Type</Label>
            <Select
              value={indicator.indicator_type}
              onValueChange={handleTypeChange}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(INDICATOR_CONFIGS).map(([key, cfg]) => (
                  <SelectItem key={key} value={key}>
                    {cfg.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Alias</Label>
            <Input
              value={indicator.alias}
              onChange={(e) => onChange({ alias: e.target.value })}
              placeholder="e.g., rsi_14"
            />
          </div>
        </div>

        {config && config.params.length > 0 && (
          <div className="space-y-2">
            <Label className="text-muted-foreground">Parameters</Label>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {config.params.map((param) => (
                <div key={param.key} className="space-y-1">
                  <Label className="text-sm">{param.label}</Label>
                  {param.type === "select" ? (
                    <Select
                      value={String(indicator.params[param.key] || param.default)}
                      onValueChange={(v) => handleParamChange(param.key, v)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {param.options?.map((opt) => (
                          <SelectItem key={opt} value={opt}>
                            {opt}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      type="number"
                      value={indicator.params[param.key] ?? param.default}
                      onChange={(e) =>
                        handleParamChange(param.key, parseFloat(e.target.value) || 0)
                      }
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {outputs.length > 0 && (
          <div className="rounded-md bg-muted/50 p-3">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium">Output columns:</span>{" "}
              {outputs.map((col, i) => (
                <code key={col} className="text-primary">
                  {col}
                  {i < outputs.length - 1 && ", "}
                </code>
              ))}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
