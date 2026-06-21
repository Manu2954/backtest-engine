import { Outlet } from "react-router-dom";
import { Navbar } from "./Navbar";

export function AppShell() {
  return (
    <div className="relative flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <div className="container py-6">
          <Outlet />
        </div>
      </main>
      <footer className="border-t py-4">
        <div className="container flex items-center justify-center text-sm text-muted-foreground">
          <p>Backtest Engine © {new Date().getFullYear()}</p>
        </div>
      </footer>
    </div>
  );
}
