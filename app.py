# =============================================================================
# app.py — The main application file
# =============================================================================
# This file does everything:
#   - Creates the database table when you first run the app
#   - Defines all the URL "routes" (pages) the app responds to
#   - Handles reading, adding, editing, and deleting trades
#   - Calculates PnL and statistics
#
# Flask is a lightweight Python web framework. It lets us run a local web
# server that our browser can talk to.
#
# This journal supports any instrument. When you add a trade, you specify the
# point value — the dollar amount a 1-point price move is worth per contract
# or share. Examples:
#   - MES (Micro E-mini S&P 500) → 5.0
#   - ES  (E-mini S&P 500)       → 50.0
#   - MNQ (Micro E-mini Nasdaq)  → 2.0
#   - Stocks (1 share = 1 unit)  → 1.0
# =============================================================================

import os
import json
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash

# --- App setup ---------------------------------------------------------------

app = Flask(__name__)

# secret_key is required by Flask to enable "flash" messages.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

DB_PATH = 'trades.db'


# --- Database helpers --------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date       TEXT    NOT NULL,
            trade_time       TEXT    NOT NULL,
            symbol           TEXT    NOT NULL DEFAULT 'MES',
            direction        TEXT    NOT NULL,
            entry_price      REAL    NOT NULL,
            exit_price       REAL    NOT NULL,
            contracts        INTEGER NOT NULL DEFAULT 1,
            point_value      REAL    NOT NULL DEFAULT 1.0,
            commission       REAL    NOT NULL DEFAULT 0.0,
            gross_pnl        REAL    NOT NULL,
            net_pnl          REAL    NOT NULL,
            bars_in_trade    INTEGER,
            exit_reason      TEXT,
            strategy_version TEXT,
            notes            TEXT
        )
    ''')
    conn.commit()
    conn.close()


# --- PnL calculation ---------------------------------------------------------

def calculate_pnl(direction, entry_price, exit_price, contracts, point_value, commission):
    """
    Calculate gross PnL and net PnL for any instrument.
    point_value is the dollar value of a 1-unit price move per contract/share.
    """
    if direction.lower() == 'long':
        gross_pnl = (exit_price - entry_price) * contracts * point_value
    else:  # short
        gross_pnl = (entry_price - exit_price) * contracts * point_value

    net_pnl = gross_pnl - commission
    return round(gross_pnl, 2), round(net_pnl, 2)


# --- Statistics calculation --------------------------------------------------

def calculate_stats(trades):
    if not trades:
        return {
            'total_trades'  : 0,
            'win_rate'      : 0.0,
            'net_pnl'       : 0.0,
            'gross_profit'  : 0.0,
            'gross_loss'    : 0.0,
            'avg_win'       : 0.0,
            'avg_loss'      : 0.0,
            'profit_factor' : 'N/A',
            'largest_winner': 0.0,
            'largest_loser' : 0.0,
        }

    total      = len(trades)
    net_pnls   = [t['net_pnl']   for t in trades]
    gross_pnls = [t['gross_pnl'] for t in trades]

    winners = [p for p in net_pnls if p > 0]
    losers  = [p for p in net_pnls if p < 0]

    gross_profit = sum(p for p in gross_pnls if p > 0)
    gross_loss   = sum(p for p in gross_pnls if p < 0)

    win_rate = (len(winners) / total * 100) if total > 0 else 0.0
    avg_win  = (sum(winners) / len(winners)) if winners else 0.0
    avg_loss = (sum(losers)  / len(losers))  if losers  else 0.0

    if gross_loss != 0:
        profit_factor = round(gross_profit / abs(gross_loss), 2)
    elif gross_profit > 0:
        profit_factor = '∞'
    else:
        profit_factor = 'N/A'

    return {
        'total_trades'  : total,
        'win_rate'      : round(win_rate, 1),
        'net_pnl'       : round(sum(net_pnls), 2),
        'gross_profit'  : round(gross_profit, 2),
        'gross_loss'    : round(gross_loss, 2),
        'avg_win'       : round(avg_win, 2),
        'avg_loss'      : round(avg_loss, 2),
        'profit_factor' : profit_factor,
        'largest_winner': round(max(net_pnls), 2) if net_pnls else 0.0,
        'largest_loser' : round(min(net_pnls), 2) if net_pnls else 0.0,
    }


# --- Routes ------------------------------------------------------------------

@app.route('/')
def index():
    conn = get_db()

    direction_filter = request.args.get('direction', '')
    date_from        = request.args.get('date_from', '')
    date_to          = request.args.get('date_to', '')

    query  = 'SELECT * FROM trades WHERE 1=1'
    params = []

    if direction_filter:
        query += ' AND direction = ?'
        params.append(direction_filter)
    if date_from:
        query += ' AND trade_date >= ?'
        params.append(date_from)
    if date_to:
        query += ' AND trade_date <= ?'
        params.append(date_to)

    query += ' ORDER BY trade_date ASC, trade_time ASC'

    filtered_trades = [dict(t) for t in conn.execute(query, params).fetchall()]

    all_trades = [dict(t) for t in conn.execute(
        'SELECT * FROM trades ORDER BY trade_date ASC, trade_time ASC'
    ).fetchall()]

    conn.close()

    long_trades  = [t for t in all_trades if t['direction'] == 'long']
    short_trades = [t for t in all_trades if t['direction'] == 'short']

    stats_all   = calculate_stats(all_trades)
    stats_long  = calculate_stats(long_trades)
    stats_short = calculate_stats(short_trades)

    equity_labels = []
    equity_values = []
    cumulative    = 0.0

    for i, t in enumerate(all_trades, start=1):
        cumulative += t['net_pnl']
        equity_labels.append(f"#{i}  {t['trade_date']}")
        equity_values.append(round(cumulative, 2))

    return render_template('index.html',
        trades          = filtered_trades,
        stats_all       = stats_all,
        stats_long      = stats_long,
        stats_short     = stats_short,
        equity_labels   = json.dumps(equity_labels),
        equity_values   = json.dumps(equity_values),
        direction_filter= direction_filter,
        date_from       = date_from,
        date_to         = date_to,
    )


@app.route('/add', methods=['GET', 'POST'])
def add_trade():
    if request.method == 'POST':
        trade_date       = request.form['trade_date']
        trade_time       = request.form['trade_time']
        symbol           = request.form['symbol']
        direction        = request.form['direction']
        entry_price      = float(request.form['entry_price'])
        exit_price       = float(request.form['exit_price'])
        contracts        = int(request.form['contracts'])
        point_value      = float(request.form['point_value'])
        commission       = float(request.form['commission'])
        bars_in_trade    = request.form.get('bars_in_trade', '').strip()
        exit_reason      = request.form.get('exit_reason', '').strip()
        strategy_version = request.form.get('strategy_version', '').strip()
        notes            = request.form.get('notes', '').strip()

        bars_in_trade = int(bars_in_trade) if bars_in_trade else None

        gross_pnl, net_pnl = calculate_pnl(
            direction, entry_price, exit_price, contracts, point_value, commission
        )

        conn = get_db()
        conn.execute('''
            INSERT INTO trades
              (trade_date, trade_time, symbol, direction,
               entry_price, exit_price, contracts, point_value, commission,
               gross_pnl, net_pnl, bars_in_trade,
               exit_reason, strategy_version, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trade_date, trade_time, symbol, direction,
              entry_price, exit_price, contracts, point_value, commission,
              gross_pnl, net_pnl, bars_in_trade,
              exit_reason, strategy_version, notes))
        conn.commit()
        conn.close()

        flash('Trade added!', 'success')
        return redirect(url_for('index'))

    today    = datetime.now().strftime('%Y-%m-%d')
    now_time = datetime.now().strftime('%H:%M')
    return render_template('add_trade.html', today=today, now_time=now_time)


@app.route('/edit/<int:trade_id>', methods=['GET', 'POST'])
def edit_trade(trade_id):
    conn = get_db()

    if request.method == 'POST':
        trade_date       = request.form['trade_date']
        trade_time       = request.form['trade_time']
        symbol           = request.form['symbol']
        direction        = request.form['direction']
        entry_price      = float(request.form['entry_price'])
        exit_price       = float(request.form['exit_price'])
        contracts        = int(request.form['contracts'])
        point_value      = float(request.form['point_value'])
        commission       = float(request.form['commission'])
        bars_in_trade    = request.form.get('bars_in_trade', '').strip()
        exit_reason      = request.form.get('exit_reason', '').strip()
        strategy_version = request.form.get('strategy_version', '').strip()
        notes            = request.form.get('notes', '').strip()

        bars_in_trade = int(bars_in_trade) if bars_in_trade else None

        gross_pnl, net_pnl = calculate_pnl(
            direction, entry_price, exit_price, contracts, point_value, commission
        )

        conn.execute('''
            UPDATE trades SET
              trade_date=?,       trade_time=?,        symbol=?,
              direction=?,        entry_price=?,       exit_price=?,
              contracts=?,        point_value=?,       commission=?,
              gross_pnl=?,        net_pnl=?,           bars_in_trade=?,
              exit_reason=?,      strategy_version=?,  notes=?
            WHERE id=?
        ''', (trade_date, trade_time, symbol, direction,
              entry_price, exit_price, contracts, point_value, commission,
              gross_pnl, net_pnl, bars_in_trade,
              exit_reason, strategy_version, notes,
              trade_id))
        conn.commit()
        conn.close()

        flash('Trade updated!', 'success')
        return redirect(url_for('index'))

    trade = conn.execute('SELECT * FROM trades WHERE id = ?', (trade_id,)).fetchone()
    conn.close()

    if trade is None:
        flash('Trade not found.', 'error')
        return redirect(url_for('index'))

    return render_template('edit_trade.html', trade=dict(trade))


@app.route('/delete/<int:trade_id>', methods=['POST'])
def delete_trade(trade_id):
    conn = get_db()
    conn.execute('DELETE FROM trades WHERE id = ?', (trade_id,))
    conn.commit()
    conn.close()
    flash('Trade deleted.', 'info')
    return redirect(url_for('index'))


# --- Entry point -------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    print()
    print('=' * 50)
    print('  Trading Journal is running!')
    print('  Open your browser and go to:')
    print('  http://127.0.0.1:5000')
    print('=' * 50)
    print()
    app.run(debug=True)
