"""Sharp-drop mean-reversion scalper for CBBTC (agent-fun/bars-replay/v1).

Strategy (original; no EMA cross, no RSI/Bollinger, no momentum rebalance):
  Bitcoin's 1-minute returns are near white noise, but a sharp 10-minute drop
  is followed, on average, by a partial bounce: on the dev window, after a
  10-minute close-to-close fall of >= 40 bps the mean 30-minute forward return
  is about +28 bps, while smaller drops (35-40 bps) do not revert enough to
  cover round-trip costs and 60-minute drops keep trending down (both tested
  and rejected). The bot buys the sharp drop and exits on a fixed asymmetric
  payoff before the bounce fades.

  Entry (flat only): the 10-minute close-to-close return is <= -40 bps.
  Size: 50% of cash. Half size halves the per-leg price impact (a $1,000 buy
  moves its own price ~8 bps against the pool; $500 moves it ~4 bps), cutting
  the round trip from ~26 bps to ~20 bps, which is what makes the thin edge
  net-positive. A full-size entry was tested and loses on the dev window.
  Exit (whole position): take profit at +60 bps of cost, stop loss at -25 bps
  of cost, or a 45-bar time stop after entry, whichever comes first.
  Cooldown: 5 bars after an exit before a new entry, so one dip is not
  re-entered bar after bar.

  All decisions use exact integer arithmetic on the bar closes (no floats, no
  wall clock, no network, no randomness, no files): two runs on the same data
  produce byte-identical replies. Orders are capped at 100 bps of slippage
  from the decision close, as the baselines do.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# Entry: 10-bar close-to-close fall of at least DROP_BPS basis points.
LOOKBACK_BARS = 10
DROP_BPS = 40
# Size: half the cash on hand.
SIZE_NUM = 1
SIZE_DEN = 2
# Exits, in basis points of the position's cost (fees included).
TAKE_PROFIT_BPS = 60
STOP_LOSS_BPS = 25
# Time stop, in bars after the entry was decided.
TIME_STOP_BARS = 45
# Bars to wait after an exit before entering again.
COOLDOWN_BARS = 5
# Max slippage allowed from the decision close, in basis points.
MAX_SLIPPAGE_BPS = 100

# Closes seen so far, oldest first, per symbol (closes are u64 strings).
_closes = []
# Seq of the bar on which the current entry was decided (-1 when flat).
_entry_seq = -1
# Seq of the bar on which the last exit was decided (-1 when none yet).
_last_exit_seq = -1


def _div_trunc(num, den):
    """Integer division truncated toward zero (unlike //, which floors)."""
    q = abs(num) // den
    return -q if num < 0 else q


def _drop_bps_now():
    """The 10-bar close-to-close return in bps, truncated toward zero, or None."""
    if len(_closes) < LOOKBACK_BARS + 1:
        return None
    now = _closes[-1]
    then = _closes[-1 - LOOKBACK_BARS]
    return _div_trunc((now - then) * 10000, then)


def on_batch(state, batch):
    global _entry_seq, _last_exit_seq
    # Only act on a symbol this batch actually carries a bar for.
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
        if _last_exit_seq >= 0 and state.seq - _last_exit_seq < COOLDOWN_BARS:
            return []
        drop = _drop_bps_now()
        if drop is not None and drop <= -DROP_BPS:
            notional = state.cash * SIZE_NUM // SIZE_DEN
            if notional < int(state.hello["fees"]["min_notional_quote_units"]):
                return []
            _entry_seq = state.seq
            return [{
                "side": "buy",
                "symbol": SYMBOL,
                "notional_quote_units": notional,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []
    # Held: whole-position exits, checked in a fixed order.
    value = state.value(SYMBOL, held.qty)
    cost = held.cost
    if cost > 0:
        # Take profit: value >= cost * (10000 + 60) / 10000.
        if value * 10000 >= cost * (10000 + TAKE_PROFIT_BPS):
            _last_exit_seq = state.seq
            _entry_seq = -1
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": held.qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        # Stop loss: value <= cost * (10000 - 25) / 10000.
        if value * 10000 <= cost * (10000 - STOP_LOSS_BPS):
            _last_exit_seq = state.seq
            _entry_seq = -1
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": held.qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
    # Time stop: 45 bars after the entry decision.
    if _entry_seq >= 0 and state.seq - _entry_seq >= TIME_STOP_BARS:
        _last_exit_seq = state.seq
        _entry_seq = -1
        return [{
            "side": "sell",
            "symbol": SYMBOL,
            "qty": held.qty,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]
    return []


makefun_bars.run(on_batch)
