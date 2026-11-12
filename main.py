"""Dip-bounce trader with staged exits for CBBTC (agent-fun/bars-replay/v1).

Design, in my own words:

  Short, sharp drops in a 1-minute price series tend to bounce part of the
  way back, while slow drifts mostly keep drifting. This bot does exactly
  one thing: it waits flat until the last 10 bars have fallen at least
  45 bps close-to-close, then it buys with all the cash it has. Smaller
  drops are ignored on purpose — their bounce, when it comes, is usually
  too small to cover the round-trip fee, slippage and price impact.

  The exit is staged rather than a single take-profit, because a bounce
  that stalls halfway is worth banking, while a strong one is worth
  riding:

    1. A stop loss at -40 bps of the position's cost (fees included) is
       always active; a dip that keeps falling is not a bounce.
    2. At +30 bps of cost, half the position is sold and banked.
    3. The remaining half is sold at +90 bps of cost, or when the
       position's value has fallen 25 bps below the highest value it
       reached since entry (a trailing stop on the remainder).
    4. Whatever is still held 90 bars after the entry decision is sold
       by a time stop, so capital is never parked in a dead position.

  There is no cooldown: after an exit the bot may buy the same dip again
  if the 10-bar fall still qualifies.

  Everything is exact integer arithmetic on the bar closes — no floats,
  no wall clock, no network, no randomness, no files — so two runs over
  the same bars produce identical orders. Orders cap slippage at 100 bps
  from the decision close.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# Entry signal: fall over the last LOOKBACK_BARS closes, in basis points.
LOOKBACK_BARS = 10
ENTRY_DROP_BPS = 45
# Exits, in basis points of the position's cost (fees included).
STOP_LOSS_BPS = 40
STAGE1_PROFIT_BPS = 30
STAGE2_PROFIT_BPS = 90
TRAILING_DROP_BPS = 25
# Bars after the entry decision at which any remainder is sold.
TIME_STOP_BARS = 90
# Max slippage allowed from the decision close, in basis points.
MAX_SLIPPAGE_BPS = 100

# Closes seen so far, oldest first (each an int of quote units).
_closes = []
# Seq of the bar on which the current entry was decided (-1 when flat).
_entry_seq = -1
# Highest value of the current position since entry (quote units).
_peak_value = 0
# Whether the stage-1 (half) sale of the current position has happened.
_sold_half = False


def _div_trunc(num, den):
    """Integer division truncated toward zero (unlike //, which floors)."""
    q = abs(num) // den
    return -q if num < 0 else q


def _ten_bar_return_bps():
    """Return over the last 10 bars in bps, truncated toward zero, or None."""
    if len(_closes) < LOOKBACK_BARS + 1:
        return None
    latest = _closes[-1]
    lookback_close = _closes[-1 - LOOKBACK_BARS]
    return _div_trunc((latest - lookback_close) * 10000, lookback_close)


def _sell_order(qty):
    return {
        "side": "sell",
        "symbol": SYMBOL,
        "qty": qty,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }


def _mark_flat():
    global _entry_seq, _sold_half
    _entry_seq = -1
    _sold_half = False


def on_batch(state, batch):
    global _entry_seq, _peak_value, _sold_half
    # Only act on a batch that actually carries a bar for our symbol.
    fresh = {bar["symbol"] for bar in batch["bars"]}
    if SYMBOL not in fresh:
        return []
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            _closes.append(int(bar["c"]))
    if state.warming_up:
        return []

    held = state.positions.get(SYMBOL)
    if held is None:
        # Flat: the only question is whether the dip qualifies as an entry.
        drop = _ten_bar_return_bps()
        if drop is not None and drop <= -ENTRY_DROP_BPS:
            notional = state.cash
            if notional < int(state.hello["fees"]["min_notional_quote_units"]):
                return []
            _entry_seq = state.seq
            _peak_value = 0
            _sold_half = False
            return [{
                "side": "buy",
                "symbol": SYMBOL,
                "notional_quote_units": notional,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []

    # Holding: remember the best value seen, then run the exits in order.
    value = state.value(SYMBOL, held.qty)
    if value > _peak_value:
        _peak_value = value
    cost = held.cost
    if cost > 0:
        # 1. Stop loss: value <= cost * (10000 - 40) / 10000.
        if value * 10000 <= cost * (10000 - STOP_LOSS_BPS):
            _mark_flat()
            return [_sell_order(held.qty)]
        # 2. Stage 1: bank half at +30 bps of cost.
        if not _sold_half and value * 10000 >= cost * (10000 + STAGE1_PROFIT_BPS):
            _sold_half = True
            return [_sell_order(held.qty // 2)]
        if _sold_half:
            # 3a. Stage 2 target: sell the rest at +90 bps of cost.
            if value * 10000 >= cost * (10000 + STAGE2_PROFIT_BPS):
                _mark_flat()
                return [_sell_order(held.qty)]
            # 3b. Trailing stop on the remainder: value has fallen 25 bps
            # below its peak value since entry.
            if _peak_value > 0 and value * 10000 <= _peak_value * (10000 - TRAILING_DROP_BPS):
                _mark_flat()
                return [_sell_order(held.qty)]
    # 4. Time stop: sell whatever remains 90 bars after the entry decision.
    if _entry_seq >= 0 and state.seq - _entry_seq >= TIME_STOP_BARS:
        _mark_flat()
        return [_sell_order(held.qty)]
    return []


makefun_bars.run(on_batch)
