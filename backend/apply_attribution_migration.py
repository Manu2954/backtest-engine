#!/usr/bin/env python
"""Apply database migration for trade attribution."""
import sys
import subprocess

print("=" * 80)
print("STEP 8: APPLYING TRADE ATTRIBUTION MIGRATION")
print("=" * 80)
print()

# Check if we're in the right directory
import os
if not os.path.exists('alembic.ini'):
    print("❌ Error: alembic.ini not found. Please run from backend directory.")
    sys.exit(1)

print("✅ Found alembic.ini")
print()

# Run alembic upgrade head
print("Running: alembic upgrade head")
print("-" * 80)
result = subprocess.run(['alembic', 'upgrade', 'head'], capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print(result.stderr)

if result.returncode == 0:
    print()
    print("=" * 80)
    print("✅ MIGRATION APPLIED SUCCESSFULLY")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Verify database schema:")
    print("   python -c \"from app.models.backtest import BacktestRun, TradeLog; print('Models loaded successfully')\"")
    print()
    print("2. Check migration status:")
    print("   alembic current")
    print()
else:
    print()
    print("=" * 80)
    print("❌ MIGRATION FAILED")
    print("=" * 80)
    sys.exit(1)
