# Trading Journal

A local trading journal application built in Python (Flask) that records trade
performance and automatically generates an updating equity curve. Built to
support disciplined forward-testing of both an algorithmic strategy and manual trading for futures before live deployment. Default inputs are for the MES1! (S&P 500 Micro E-mini)

## Features
- Records date, time, symbol, direction, entry/exit prices, contracts, point value, commission, and trade notes
- Stores trades locally in a SQLite database
- Auto-calculates gross PnL and net PnL for any instrument (futures, stocks)
- Auto-generates and updates an equity curve as new trades are logged
- Filters trades by direction and date range
- Displays summary statistics: win rate, profit factor, average win/loss, largest winner/loser, gross profit/loss
- Separate stats panels for all trades, longs only, and shorts only

## Tech Stack
- Python 3
- Flask (web framework)
- SQLite (local database)
- Chart.js (equity curve visualization)
- HTML / CSS / JavaScript (frontend)
- Built with assistance from Claude Code

## Running Locally
1. Clone or download this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `python app.py`
4. Open `http://127.0.0.1:5000` in your browser

## Context
Built in March 2026 as part of a self-directed project to forward-test a
Pine Script V6 volume-breakout strategy on MES (Micro E-mini S&P 500) futures.
The journal supports any instrument by allowing the user to specify the
point value per trade. I hope this app can help everyone else with their personal trading journey.

## NOTE
Assumes zero slippage and this is not adjustable currently.
