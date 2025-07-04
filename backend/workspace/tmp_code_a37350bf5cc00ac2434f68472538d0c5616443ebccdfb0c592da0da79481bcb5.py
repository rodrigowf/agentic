#!/usr/bin/env python3
"""
msft_yearly_plot.py

Fetches one year of Microsoft (MSFT) daily stock data from Yahoo Finance
and plots the closing price over time.
"""

import sys
import datetime

try:
    import yfinance as yf
    import matplotlib.pyplot as plt
except ImportError as e:
    missing = e.name
    print(f"Error: missing module '{missing}'.")
    print("Install dependencies with:\n    pip install yfinance matplotlib")
    sys.exit(1)


def fetch_and_plot(ticker: str, days: int = 365) -> None:
    """Fetches the last `days` of `ticker` data and plots the Close price."""
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=days)

    # Download data
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    if df.empty:
        print(f"No data fetched for {ticker}. Check ticker symbol or your network.")
        return

    # Plot
    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df['Close'], color='navy', linewidth=1.5, label=f'{ticker} Close')
    plt.title(f"{ticker} Closing Price — Last {days} Days")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # By default, plot MSFT for the last 365 days
    fetch_and_plot("MSFT", days=365)
