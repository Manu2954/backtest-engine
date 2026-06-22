import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Pencil, Trash2, Play, Loader2 } from "lucide-react";
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
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { useStrategies, useDeleteStrategy } from "@/api/hooks";
import type { Strategy } from "@/types";

export default function StrategyList() {
  const { data: strategies, isLoading, error } = useStrategies();
  const deleteStrategy = useDeleteStrategy();
  const [deleteTarget, setDeleteTarget] = useState<Strategy | null>(null);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteStrategy.mutateAsync(deleteTarget.id);
      setDeleteTarget(null);
    } catch (error) {
      console.error("Failed to delete strategy:", error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Failed to load strategies: {error.message}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Strategies</h1>
          <p className="text-muted-foreground">
            Manage your trading strategies
          </p>
        </div>
        <Link to="/strategies/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Strategy
          </Button>
        </Link>
      </div>

      {!strategies || strategies.length === 0 ? (
        <EmptyState
          title="No strategies yet"
          description="Create your first trading strategy to get started."
          action={
            <Link to="/strategies/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Strategy
              </Button>
            </Link>
          }
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Your Strategies</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Indicators</TableHead>
                  <TableHead>Conditions</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {strategies.map((strategy) => {
                  const entryConditions = strategy.condition_groups
                    .filter((g) => g.group_type === "ENTRY")
                    .reduce((sum, g) => sum + g.conditions.length, 0);
                  const exitConditions = strategy.condition_groups
                    .filter((g) => g.group_type === "EXIT")
                    .reduce((sum, g) => sum + g.conditions.length, 0);

                  return (
                    <TableRow key={strategy.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{strategy.name}</p>
                          {strategy.description && (
                            <p className="text-sm text-muted-foreground truncate max-w-[300px]">
                              {strategy.description}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{strategy.indicators.length}</TableCell>
                      <TableCell>
                        {entryConditions} entry / {exitConditions} exit
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link to={`/strategies/${strategy.id}`}>
                            <Button variant="ghost" size="icon">
                              <Pencil className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Button variant="ghost" size="icon" asChild>
                            <Link to={`/backtests?strategy=${strategy.id}`}>
                              <Play className="h-4 w-4" />
                            </Link>
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteTarget(strategy)}
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

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete Strategy"
        description={`Are you sure you want to delete "${deleteTarget?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={handleDelete}
        variant="destructive"
      />
    </div>
  );
}
