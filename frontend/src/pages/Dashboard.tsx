import { Link } from "react-router-dom";
import {
  BarChart3,
  LineChart,
  Plus,
  TrendingUp,
  Zap,
  Shield,
  Target,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const features = [
  {
    icon: TrendingUp,
    title: "Technical Indicators",
    description:
      "RSI, MACD, Bollinger Bands, ATR, and more. Build complex strategies with multiple indicators.",
  },
  {
    icon: Target,
    title: "Flexible Conditions",
    description:
      "Crossovers, comparisons, and boolean expressions. Define precise entry and exit rules.",
  },
  {
    icon: LineChart,
    title: "Realistic Simulation",
    description:
      "Commission, slippage, position sizing, and risk management. See true performance.",
  },
  {
    icon: Shield,
    title: "Risk Management",
    description:
      "Stop loss, take profit, and dynamic trailing stops. Protect your capital.",
  },
  {
    icon: BarChart3,
    title: "Performance Analytics",
    description:
      "Sharpe ratio, max drawdown, win rate, and more. Understand your strategy's edge.",
  },
  {
    icon: Zap,
    title: "Robustness Testing",
    description:
      "Parameter sensitivity, walk-forward validation, and regime analysis.",
  },
];

export default function Dashboard() {
  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="flex flex-col items-center text-center space-y-4 py-8">
        <div className="inline-flex items-center rounded-full border px-3 py-1 text-sm">
          <span className="text-primary">Professional Backtesting Platform</span>
        </div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Test Your Trading Strategies
        </h1>
        <p className="max-w-[600px] text-muted-foreground text-lg">
          Build, backtest, and analyze trading strategies with realistic
          simulation. Support for stocks and crypto with comprehensive
          performance metrics.
        </p>
        <div className="flex gap-4">
          <Link to="/strategies/new">
            <Button size="lg" className="gap-2">
              <Plus className="h-4 w-4" />
              Create Strategy
            </Button>
          </Link>
          <Link to="/strategies">
            <Button size="lg" variant="outline">
              View Strategies
            </Button>
          </Link>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <Card key={feature.title}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="rounded-lg bg-primary/10 p-2">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription>{feature.description}</CardDescription>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Start</CardTitle>
          <CardDescription>
            Get started with a new strategy or view your existing work
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <Link to="/strategies/new" className="block">
            <div className="rounded-lg border p-4 hover:bg-accent transition-colors">
              <Plus className="h-8 w-8 text-primary mb-2" />
              <h3 className="font-medium">New Strategy</h3>
              <p className="text-sm text-muted-foreground">
                Create a new trading strategy
              </p>
            </div>
          </Link>
          <Link to="/strategies" className="block">
            <div className="rounded-lg border p-4 hover:bg-accent transition-colors">
              <TrendingUp className="h-8 w-8 text-primary mb-2" />
              <h3 className="font-medium">My Strategies</h3>
              <p className="text-sm text-muted-foreground">
                View and manage strategies
              </p>
            </div>
          </Link>
          <Link to="/backtests" className="block">
            <div className="rounded-lg border p-4 hover:bg-accent transition-colors">
              <BarChart3 className="h-8 w-8 text-primary mb-2" />
              <h3 className="font-medium">Backtest Results</h3>
              <p className="text-sm text-muted-foreground">
                View backtest history
              </p>
            </div>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
