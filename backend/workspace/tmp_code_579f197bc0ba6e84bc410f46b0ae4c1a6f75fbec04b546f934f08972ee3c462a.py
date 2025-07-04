#!/usr/bin/env python3
"""
msft_plot.py

Fetch & plot MSFT closing prices for the past year.
Auto-installs dependencies, supports headless mode.
"""

import sys
import subprocess
import datetime
import argparse

def ensure_package(pkg_name):
    try:
        __import__(pkg_name)
    except ImportError:
        print(f"[+] Installing {pkg_name}…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
    finally:
        return __import__(pkg_name)

# 1) Ensure & import deps
yfinance = ensure_package("yfinance")
matplotlib = ensure_package("matplotlib")
# If headless flag is used, we’ll switch backend after parsing args
plt = None

def parse_args():
    p = argparse.ArgumentParser(description="Plot MSFT last year closing price")
    p.add_argument("--headless", action="store_true",
                   help="Use Agg backend and save plot instead of showing")
    p.add_argument("--outfile", type=str, default="msft_last_year.png",
                   help="Output file (PNG) when headless")
    return p.parse_args()

def fetch_data(ticker="MSFT", days=365):
    end = datetime.datetime.today()
    start = end - datetime.timedelta(days=days)
    df = yfinance.download(ticker, start=start, end=end, progress=False)
    if df.empty:
        print("❌ No data fetched. Exiting.")
        sys.exit(1)
    return df

def plot_df(df, ticker, headless=False, outfile=None):
    global plt
    if headless:
        matplotlib.use("Agg")
    import matplotlib.pyplot as _plt
    plt = _plt

    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df["Close"], color="navy", lw=1.5, label=f"{ticker} Close")
    plt.title(f"{ticker} Closing Price — Last Year")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    if headless:
        print(f"[+] Saving plot to {outfile}")
        plt.savefig(outfile, dpi=150)
    else:
        plt.show()

def main():
    args = parse_args()
    ticker = "MSFT"
    df = fetch_data(ticker, days=365)
    plot_df(df, ticker, headless=args.headless, outfile=args.outfile)

if __name__ == "__main__":
    main()
