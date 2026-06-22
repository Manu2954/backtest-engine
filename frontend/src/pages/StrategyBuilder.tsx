import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Plus, ArrowLeft, ArrowRight, Save, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { WizardStepper } from "@/components/strategy/WizardStepper";
import { IndicatorCard } from "@/components/strategy/IndicatorCard";
import { ConditionGroup } from "@/components/strategy/ConditionGroup";
import { useStrategyBuilderStore } from "@/store/strategyBuilder";
import { useStrategy, useCreateStrategy, useUpdateStrategy } from "@/api/hooks";
import { ASSET_CLASSES, BAR_RESOLUTIONS, POSITION_SIZE_TYPES } from "@/lib/constants";

const STEPS = [
  { title: "Indicators", description: "Add technical indicators" },
  { title: "Entry Rules", description: "Define entry conditions" },
  { title: "Exit Rules", description: "Define exit conditions" },
  { title: "Backtest", description: "Configure backtest parameters" },
  { title: "Review", description: "Review and save" },
];

export default function StrategyBuilder() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditMode = !!id;

  const { data: existingStrategy, isLoading: isLoadingStrategy } = useStrategy(id);
  const createStrategy = useCreateStrategy();
  const updateStrategy = useUpdateStrategy();

  const {
    name,
    description,
    currentStep,
    indicators,
    entryGroup,
    exitGroup,
    backtestConfig,
    setName,
    setDescription,
    setCurrentStep,
    nextStep,
    prevStep,
    addIndicator,
    updateIndicator,
    removeIndicator,
    addEntryCondition,
    addExitCondition,
    updateEntryCondition,
    updateExitCondition,
    removeEntryCondition,
    removeExitCondition,
    setEntryLogic,
    setExitLogic,
    updateBacktestConfig,
    reset,
    loadStrategy,
  } = useStrategyBuilderStore();

  // Load existing strategy
  useEffect(() => {
    if (existingStrategy && isEditMode) {
      loadStrategy(existingStrategy);
    }
  }, [existingStrategy, isEditMode, loadStrategy]);

  // Reset on unmount
  useEffect(() => {
    return () => {
      if (!isEditMode) {
        reset();
      }
    };
  }, [isEditMode, reset]);

  const handleSave = async () => {
    const strategyData = {
      name,
      description: description || undefined,
      indicators: indicators.map((ind, i) => ({
        ...ind,
        display_order: i,
      })),
      entry: {
        logic: entryGroup.logic,
        conditions: entryGroup.conditions.map((c, i) => ({
          ...c,
          display_order: i,
        })),
      },
      exit: {
        logic: exitGroup.logic,
        conditions: exitGroup.conditions.map((c, i) => ({
          ...c,
          display_order: i,
        })),
      },
    };

    try {
      if (isEditMode && id) {
        await updateStrategy.mutateAsync({ id, data: strategyData });
      } else {
        await createStrategy.mutateAsync(strategyData);
      }
      navigate("/strategies");
    } catch (error) {
      console.error("Failed to save strategy:", error);
    }
  };

  const isSaving = createStrategy.isPending || updateStrategy.isPending;

  if (isLoadingStrategy) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          {isEditMode ? "Edit Strategy" : "New Strategy"}
        </h1>
        <p className="text-muted-foreground">
          Build your trading strategy step by step
        </p>
      </div>

      <WizardStepper
        steps={STEPS}
        currentStep={currentStep}
        onStepClick={setCurrentStep}
      />

      {/* Step 0: Indicators */}
      {currentStep === 0 && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Strategy Name *</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Strategy"
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
              />
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Indicators</h2>
              <Button onClick={addIndicator} size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Indicator
              </Button>
            </div>

            {indicators.length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center text-muted-foreground">
                  No indicators yet. Add one to get started.
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {indicators.map((indicator, index) => (
                  <IndicatorCard
                    key={index}
                    indicator={indicator}
                    index={index}
                    onChange={(ind) => updateIndicator(index, ind)}
                    onRemove={() => removeIndicator(index)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 1: Entry Rules */}
      {currentStep === 1 && (
        <ConditionGroup
          title="Entry Conditions"
          description="Define when to enter a trade"
          group={entryGroup}
          indicators={indicators}
          onLogicChange={setEntryLogic}
          onConditionChange={updateEntryCondition}
          onConditionAdd={addEntryCondition}
          onConditionRemove={removeEntryCondition}
        />
      )}

      {/* Step 2: Exit Rules */}
      {currentStep === 2 && (
        <ConditionGroup
          title="Exit Conditions"
          description="Define when to exit a trade"
          group={exitGroup}
          indicators={indicators}
          onLogicChange={setExitLogic}
          onConditionChange={updateExitCondition}
          onConditionAdd={addExitCondition}
          onConditionRemove={removeExitCondition}
        />
      )}

      {/* Step 3: Backtest Config */}
      {currentStep === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Backtest Configuration</CardTitle>
            <CardDescription>
              Configure parameters for running backtests
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <Label>Ticker *</Label>
                <Input
                  value={backtestConfig.ticker}
                  onChange={(e) => updateBacktestConfig({ ticker: e.target.value.toUpperCase() })}
                  placeholder="AAPL, BTCUSDT, etc."
                />
              </div>
              <div className="space-y-2">
                <Label>Asset Class</Label>
                <Select
                  value={backtestConfig.assetClass}
                  onValueChange={(v) => updateBacktestConfig({ assetClass: v as "STOCK" | "CRYPTO" })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ASSET_CLASSES.map((ac) => (
                      <SelectItem key={ac.value} value={ac.value}>
                        {ac.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Resolution</Label>
                <Select
                  value={backtestConfig.barResolution}
                  onValueChange={(v) => updateBacktestConfig({ barResolution: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {BAR_RESOLUTIONS.map((br) => (
                      <SelectItem key={br.value} value={br.value}>
                        {br.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={backtestConfig.startDate}
                  onChange={(e) => updateBacktestConfig({ startDate: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>End Date</Label>
                <Input
                  type="date"
                  value={backtestConfig.endDate}
                  onChange={(e) => updateBacktestConfig({ endDate: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Initial Capital</Label>
                <Input
                  type="number"
                  value={backtestConfig.initialCapital}
                  onChange={(e) => updateBacktestConfig({ initialCapital: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-medium">Position Sizing</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Sizing Type</Label>
                  <Select
                    value={backtestConfig.positionSizeType}
                    onValueChange={(v) => updateBacktestConfig({ positionSizeType: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {POSITION_SIZE_TYPES.map((ps) => (
                        <SelectItem key={ps.value} value={ps.value}>
                          {ps.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>
                    {backtestConfig.positionSizeType === "percent_capital"
                      ? "Percentage"
                      : backtestConfig.positionSizeType === "fixed_amount"
                        ? "Amount ($)"
                        : "Value"}
                  </Label>
                  <Input
                    type="number"
                    value={backtestConfig.positionSizeValue}
                    onChange={(e) => updateBacktestConfig({ positionSizeValue: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-medium">Risk Management</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Stop Loss (%)</Label>
                  <Input
                    type="number"
                    value={backtestConfig.stopLossPct ?? ""}
                    onChange={(e) => updateBacktestConfig({
                      stopLossPct: e.target.value ? parseFloat(e.target.value) : null
                    })}
                    placeholder="Optional"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Take Profit (%)</Label>
                  <Input
                    type="number"
                    value={backtestConfig.takeProfitPct ?? ""}
                    onChange={(e) => updateBacktestConfig({
                      takeProfitPct: e.target.value ? parseFloat(e.target.value) : null
                    })}
                    placeholder="Optional"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-medium">Transaction Costs</h3>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label>Commission per Trade ($)</Label>
                  <Input
                    type="number"
                    value={backtestConfig.commissionPerTrade}
                    onChange={(e) => updateBacktestConfig({ commissionPerTrade: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Commission (%)</Label>
                  <Input
                    type="number"
                    value={backtestConfig.commissionPct}
                    onChange={(e) => updateBacktestConfig({ commissionPct: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Slippage (%)</Label>
                  <Input
                    type="number"
                    value={backtestConfig.slippagePct}
                    onChange={(e) => updateBacktestConfig({ slippagePct: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Review */}
      {currentStep === 4 && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Strategy Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-muted-foreground">Name</Label>
                <p className="font-medium">{name || "Unnamed Strategy"}</p>
              </div>
              {description && (
                <div>
                  <Label className="text-muted-foreground">Description</Label>
                  <p>{description}</p>
                </div>
              )}
              <div>
                <Label className="text-muted-foreground">Indicators</Label>
                <p>{indicators.length} configured</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Entry Conditions</Label>
                <p>
                  {entryGroup.conditions.length} condition(s) with {entryGroup.logic} logic
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Exit Conditions</Label>
                <p>
                  {exitGroup.conditions.length} condition(s) with {exitGroup.logic} logic
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Backtest Configuration</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2 sm:grid-cols-2">
              <div>
                <Label className="text-muted-foreground">Ticker</Label>
                <p>{backtestConfig.ticker || "Not set"}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Asset Class</Label>
                <p>{backtestConfig.assetClass}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Date Range</Label>
                <p>
                  {backtestConfig.startDate || "?"} to {backtestConfig.endDate || "?"}
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Initial Capital</Label>
                <p>${backtestConfig.initialCapital.toLocaleString()}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4 border-t">
        <Button
          variant="outline"
          onClick={prevStep}
          disabled={currentStep === 0}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Previous
        </Button>

        {currentStep < STEPS.length - 1 ? (
          <Button onClick={nextStep}>
            Next
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        ) : (
          <Button onClick={handleSave} disabled={isSaving || !name}>
            {isSaving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            {isEditMode ? "Update Strategy" : "Save Strategy"}
          </Button>
        )}
      </div>
    </div>
  );
}
