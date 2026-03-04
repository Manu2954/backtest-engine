from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.engine.data_layer import STOCK_INTRADAY_RESOLUTIONS, fetch_ohlcv_async


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _daterange_chunks(start: date, end: date, days: int) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=days), end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


async def _run_backfill(
    tickers: list[str],
    asset_class: str,
    resolutions: list[str],
    start: date,
    end: date,
    chunk_days: int | None,
) -> None:
    engine = create_async_engine(settings.database_url, echo=False, future=True, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        for ticker in tickers:
            for resolution in resolutions:
                if asset_class.upper() == "STOCK" and resolution in STOCK_INTRADAY_RESOLUTIONS:
                    days = chunk_days or 60
                    chunks = _daterange_chunks(start, end, days)
                else:
                    days = chunk_days or 365
                    chunks = _daterange_chunks(start, end, days)

                for chunk_start, chunk_end in chunks:
                    print(
                        f"Backfill {ticker} {asset_class} {resolution} {chunk_start} -> {chunk_end}"
                    )
                    await fetch_ohlcv_async(
                        ticker,
                        chunk_start,
                        chunk_end,
                        resolution=resolution,
                        asset_class=asset_class,
                        session=session,
                    )

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill OHLCV data into DB")
    parser.add_argument("--tickers", required=True, help="Comma-separated tickers")
    parser.add_argument("--asset", default="STOCK", help="STOCK or CRYPTO")
    parser.add_argument("--resolutions", default="1d", help="Comma-separated resolutions")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=None,
        help="Override chunk size in days (optional)",
    )

    args = parser.parse_args()
    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    resolutions = [r.strip() for r in args.resolutions.split(",") if r.strip()]

    asyncio.run(
        _run_backfill(
            tickers=tickers,
            asset_class=args.asset,
            resolutions=resolutions,
            start=_parse_date(args.start),
            end=_parse_date(args.end),
            chunk_days=args.chunk_days,
        )
    )


if __name__ == "__main__":
    main()
