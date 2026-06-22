import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Plus, Eye, Loader2, Trash2, Play, CheckCircle, XCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/shared/EmptyState";
import { useStrategies, useBacktests, useCreateBacktest, useDeleteBacktest } from "@/api/hooks";
import { formatPercent, formatDate } from "@/lib/utils";
import { ASSET_CLASSES, BAR_RESOLUTIONS, POSITION_SIZE_TYPES } from "@/lib/constants";
import type { BacktestRun } from "@/types";

const STATUS_CONFIG = {
  PENDING: { icon: Clock, color: "bg-yellow-500", label: "Pending" },
  RUNNING: { icon: Loader2, color: "bg-blue-500", label: "Running" },
  COMPLETED: { icon: CheckCircle, color: "bg-green-500", label: "Completed" },
  FAILED: { icon: XCircle, color: "bg-red-500", label: "Failed" },
};

export default function BacktestList() {
  const [searchParams] = useSearchParams();
  const strategyFilter = searchParams.get("strategy");

  const { data: strategies, isLoading: isLoadingStrategies } = useStrategies();
  const { data: backtests, isLoading: isLoadingBacktests } = useBacktests();
  const createBacktest = useCreateBacktest();
  const deleteBacktest = useDeleteBacktest();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<BacktestRun | null>(null);
  const [createForm, setCreateForm] = useState({
    strategy_id: strategyFilter || "",
    ticker: "AAPL",
    asset_class: "STOCK",
    bar_resolution: "1d",
    start_date: "2023-01-01",
    end_date: "2024-01-01",
    initial_capital: 100000,
    position_size_type: "full_capital",
    position_size_value: 100,
    stop_loss_pct: null as number | null,
    take_profit_pct: null as number | null,
    commission_per_trade: 0,
    commission_pct: 0,
    slippage_pct: 0,
  });

  const handleCreate = async () => {
    try {
      await createBacktest.mutateAsync({
        strategy_id: createForm.strategy_id,
        ticker: createForm.ticker,
        asset_class: createForm.asset_class,
        bar_resolution: createForm.bar_resolution,
        start_date: createForm.start_date,
        end_date: createForm.end_date,
        initial_capital: createForm.initial_capital,
        position_size_type: createForm.position_size_type,
        position_size_value: createForm.position_size_value,
        stop_loss_pct: createForm.stop_loss_pct,
        take_profit_pct: createForm.take_profit_pct,
        commission_per_trade: createForm.commission_per_trade,
        commission_pct: createForm.commission_pct,
        slippage_pct: createForm.slippage_pct,
      });
      setIsCreateOpen(false);
    } catch (error) {
      console.error("Failed to create backtest:", error);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteBacktest.mutateAsync(deleteTarget.id);
      setDeleteTarget(null);
    } catch (error) {
      console.error("Failed to delete backtest:", error);
    }
  };

  // Filter backtests if strategy filter is present
  const filteredBacktests = strategyFilter
    ? backtests?.filter((bt) => bt.strategy_id === strategyFilter)
    : backtests;

  const isLoading = isLoadingStrategies || isLoadingBacktests;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Backtests</h1>
          <p className="text-muted-foreground">
            View and run strategy backtests
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Backtest
        </Button>
      </div>

      {!filteredBacktests || filteredBacktests.length === 0 ? (
        <EmptyState
          title="No backtests yet"
          description="Run your first backtest to see results here."
          action={
            <Button onClick={() => setIsCreateOpen(true)}>
              <Play className="h-4 w-4 mr-2" />
              Run Backtest
            </Button>
          }
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Backtest Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Ticker</TableHead>
                  <TableHead>Date Range</TableHead>
                  <TableHead className="text-right">Return</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredBacktests.map((backtest) => {
                  const status = STATUS_CONFIG[backtest.status as keyof typeof STATUS_CONFIG];
                  const StatusIcon = status?.icon || Clock;
                  const strategy = strategies?.find((s) => s.id === backtest.strategy_id);
                  const totalReturn = backtest.results?.total_return;

                  return (
                    <TableRow key={backtest.id}>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className="gap-1"
                        >
                          <StatusIcon
                            className={`h-3 w-3 ${
                              backtest.status === "RUNNING" ? "animate-spin" : ""
                            }`}
                          />
                          {status?.label || backtest.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {strategy?.name || "Unknown Strategy"}
                      </TableCell>
                      <TableCell>{backtest.ticker}</TableCell>
                      <TableCell>
                        {formatDate(backtest.start_date)} - {formatDate(backtest.end_date)}
                      </TableCell>
                      <TableCell className="text-right">
                        {totalReturn !== undefined ? (
                          <span
                            className={
                              totalReturn >= 0 ? "text-green-500" : "text-red-500"
                            }
                          >
                            {formatPercent(totalReturn)}
                          </span>
                        ) : (
                          "-"
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {backtest.status === "COMPLETED" && (
                            <Link to={`/backtests/${backtest.id}`}>
                              <Button variant="ghost" size="icon">
                                <Eye className="h-4 w-4" />
                              </Button>
                            </Link>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteTarget(backtest)}
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Create Backtest Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Run New Backtest</DialogTitle>
            <DialogDescription>
              Configure and run a backtest for your strategy
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Strategy *</Label>
              <Select
                value={createForm.strategy_id}
                onValueChange={(v) => setCreateForm({ ...createForm, strategy_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a strategy" />
                </SelectTrigger>
                <SelectContent>
                  {strategies?.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label>Ticker</Label>
                <Input
                  value={createForm.ticker}
                  onChange={(e) => setCreateForm({ ...createForm, ticker: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="space-y-2">
                <Label>Asset Class</Label>
                <Select
                  value={createForm.asset_class}
                  onValueChange={(v) => setCreateForm({ ...createForm, asset_class: v })}
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
                  value={createForm.bar_resolution}
                  onValueChange={(v) => setCreateForm({ ...createForm, bar_resolution: v })}
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
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={createForm.start_date}
                  onChange={(e) => setCreateForm({ ...createForm, start_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>End Date</Label>
                <Input
                  type="date"
                  value={createForm.end_date}
                  onChange={(e) => setCreateForm({ ...createForm, end_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Initial Capital</Label>
                <Input
                  type="number"
                  value={createForm.initial_capital}
                  onChange={(e) => setCreateForm({ ...createForm, initial_capital: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Position Size Type</Label>
                <Select
                  value={createForm.position_size_type}
                  onValueChange={(v) => setCreateForm({ ...createForm, position_size_type: v })}
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
                <Label>Position Size Value</Label>
                <Input
                  type="number"
                  value={createForm.position_size_value}
                  onChange={(e) => setCreateForm({ ...createForm, position_size_value: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Stop Loss (%)</Label>
                <Input
                  type="number"
                  value={createForm.stop_loss_pct ?? ""}
                  onChange={(e) => setCreateForm({ ...createForm, stop_loss_pct: e.target.value ? parseFloat(e.target.value) : null })}
                  placeholder="Optional"
                />
              </div>
              <div className="space-y-2">
                <Label>Take Profit (%)</Label>
                <Input
                  type="number"
                  value={createForm.take_profit_pct ?? ""}
                  onChange={(e) => setCreateForm({ ...createForm, take_profit_pct: e.target.value ? parseFloat(e.target.value) : null })}
                  placeholder="Optional"
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label>Commission ($)</Label>
                <Input
                  type="number"
                  value={createForm.commission_per_trade}
                  onChange={(e) => setCreateForm({ ...createForm, commission_per_trade: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Commission (%)</Label>
                <Input
                  type="number"
                  value={createForm.commission_pct}
                  onChange={(e) => setCreateForm({ ...createForm, commission_pct: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Slippage (%)</Label>
                <Input
                  type="number"
                  value={createForm.slippage_pct}
                  onChange={(e) => setCreateForm({ ...createForm, slippage_pct: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!createForm.strategy_id || createBacktest.isPending}
            >
              {createBacktest.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              Run Backtest
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Backtest</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this backtest run? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteBacktest.isPending}
            >
              {deleteBacktest.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
