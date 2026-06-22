import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useBacktestTrades } from "@/api/hooks";
import { formatCurrency, formatPercent, formatDate } from "@/lib/utils";

export default function TradeLog() {
  const { id } = useParams<{ id: string }>();
  const { data: trades, isLoading, error } = useBacktestTrades(id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link to={`/backtests/${id}`}>
          <Button variant="ghost">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Report
          </Button>
        </Link>
        <div className="text-center py-8 text-destructive">
          {error.message || "Failed to load trades"}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to={`/backtests/${id}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Trade Log</h1>
          <p className="text-muted-foreground">
            {trades?.length || 0} trades
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Trades</CardTitle>
        </CardHeader>
        <CardContent>
          {!trades || trades.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No trades recorded
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>#</TableHead>
                    <TableHead>Direction</TableHead>
                    <TableHead>Entry Date</TableHead>
                    <TableHead className="text-right">Entry Price</TableHead>
                    <TableHead>Exit Date</TableHead>
                    <TableHead className="text-right">Exit Price</TableHead>
                    <TableHead className="text-right">Shares</TableHead>
                    <TableHead className="text-right">P&L</TableHead>
                    <TableHead className="text-right">P&L %</TableHead>
                    <TableHead>Exit Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {trades.map((trade, index) => {
                    const isProfit = trade.pnl >= 0;
                    return (
                      <TableRow key={index}>
                        <TableCell className="text-muted-foreground">
                          {index + 1}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={trade.direction === "LONG" ? "default" : "secondary"}
                          >
                            {trade.direction || "LONG"}
                          </Badge>
                        </TableCell>
                        <TableCell>{formatDate(trade.entry_date)}</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(trade.entry_price)}
                        </TableCell>
                        <TableCell>{formatDate(trade.exit_date)}</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(trade.exit_price)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {trade.shares.toFixed(4)}
                        </TableCell>
                        <TableCell
                          className={`text-right font-mono ${
                            isProfit ? "text-green-500" : "text-red-500"
                          }`}
                        >
                          {formatCurrency(trade.pnl)}
                        </TableCell>
                        <TableCell
                          className={`text-right font-mono ${
                            isProfit ? "text-green-500" : "text-red-500"
                          }`}
                        >
                          {formatPercent(trade.pnl_pct)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{trade.exit_reason || "signal"}</Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {trades && trades.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="text-sm text-muted-foreground">Total P&L</p>
                <p
                  className={`text-2xl font-bold ${
                    trades.reduce((sum, t) => sum + t.pnl, 0) >= 0
                      ? "text-green-500"
                      : "text-red-500"
                  }`}
                >
                  {formatCurrency(trades.reduce((sum, t) => sum + t.pnl, 0))}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Winning Trades</p>
                <p className="text-2xl font-bold text-green-500">
                  {trades.filter((t) => t.pnl >= 0).length}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Losing Trades</p>
                <p className="text-2xl font-bold text-red-500">
                  {trades.filter((t) => t.pnl < 0).length}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Avg Trade</p>
                <p
                  className={`text-2xl font-bold ${
                    trades.reduce((sum, t) => sum + t.pnl, 0) / trades.length >= 0
                      ? "text-green-500"
                      : "text-red-500"
                  }`}
                >
                  {formatCurrency(
                    trades.reduce((sum, t) => sum + t.pnl, 0) / trades.length
                  )}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
