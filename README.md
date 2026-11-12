# Dip-Bounce Trader with a Bar-Shape Entry Filter — CBBTC

A Python trading bot for the `agent-fun/bars-replay/v1` protocol. It
trades one asset, Coinbase Wrapped BTC (CBBTC) against USDC, on 1-minute
bars with paper money, and talks to the environment through the vendored
protocol shim in `vendor/`.

## What it does

The bot trades a single pattern: the bounce after a fast, deep drop.
Slow slides are left alone — they tend to keep sliding — but a fall of
at least 45 bps over the last 10 bars is sharp enough that part of it
usually comes back. The bot buys that fall, but only when the bar that
completes the signal has the right shape:

- **Bar-shape entry condition.** Because orders fill at the next bar's
  open, the bounce must not have started yet when the signal bar
  closes. The bar must close in the lowest 40% of its own high–low
  range — sellers still had the upper hand at the close, so the fill
  still gets dip prices — yet not exactly at its low. A close pinned to
  the very bottom means no buyer appeared during the entire minute,
  which is what a fall with no floor looks like; requiring the close to
  sit just above the low asks for the first sign of buying at the lows
  while the price is still depressed. Flat bars (high equal to low)
  never qualify.
- **Entry.** While flat and both conditions hold — the 10-bar fall of
  at least 45 bps and the bar shape above — the bot buys with all of
  its cash.
- **Exit, in stages.**
  1. a stop loss at −40 bps of the position's cost is always active;
  2. at +30 bps of cost, half the position is sold and banked;
  3. the other half is sold at +90 bps of cost, or once its value has
     fallen 25 bps below the highest value it reached since entry;
  4. anything still held 90 bars after entry is sold by a time stop.

There is no cooldown after an exit: if the fall still qualifies on the
next bar and the shape is right, the bot buys again.

All decisions are exact integer arithmetic on the bar prices — no
floats, no clock, no randomness, no files — so repeated runs over the
same bars give identical orders. Every order caps slippage at 100 bps
from the decision close.

## Layout

- `main.py` — the bot itself (the entry point; it registers its
  `on_batch` handler with the shim).
- `vendor/makefun_bars.py` — the competition's protocol shim, vendored
  unmodified.
- `.makefun/owner.json` — the claim file naming the entry wallet.

## License

MIT — see `LICENSE`.
