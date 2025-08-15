import tkinter as tk
import requests

def fetch_price():
    """
    Fetch the latest MSFT price from Yahoo Finance and update the label.
    Re-schedules itself to run again in 60 seconds.
    """
    try:
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        params = {"symbols": "MSFT"}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        js = resp.json()

        # drill down to the price
        price = js["quoteResponse"]["result"][0]["regularMarketPrice"]
        label.config(text=f"Microsoft (MSFT) stock price:\n${price:.2f}")
    except Exception as e:
        label.config(text="Error fetching price:\n" + str(e))

    # schedule next fetch in 60 000 ms = 60 s
    root.after(60_000, fetch_price)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("MSFT Stock Price")

    # simple styling
    label = tk.Label(
        root,
        text="Fetching price…",
        font=("Helvetica", 16),
        justify="center",
        padx=20,
        pady=20
    )
    label.pack()

    # kick off the first fetch
    fetch_price()

    root.mainloop()
