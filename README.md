# Dip-Bounce Trader with Staged Exits — CBBTC

A Python trading bot for the `agent-fun/bars-replay/v1` protocol. It
trades one asset, Coinbase Wrapped BTC (CBBTC) against USDC, on 1-minute
bars with paper money, and speaks to the environment through the vendored
protocol shim in `vendor/`.

## What it does

Minute-to-minute prices are noisy, but a fast, deep drop tends to bounce
part of the way back, while a slow slide tends to keep sliding. The bot
trades only that one pattern and ignores everything else:

- **Entry.** While flat, it watches the return over the last 10 bars. If
  the price has fallen at least 45 bps close-to-close, it buys with all
  of its cash. Shallower dips are skipped: their rebounds are usually
  too small to pay for the round trip of fees, slippage and price impact.
- **Exit, in stages.** A single fixed take-profit either cuts a good
  bounce short or gives a weak one back, so the exit is split:
  1. a stop loss at −40 bps of the position's cost is always active;
  2. at +30 bps of cost, half the position is sold and banked;
  3. the other half is sold at +90 bps of cost, or once its value has
     fallen 25 bps below the highest value it reached since entry;
  4. anything still held 90 bars after entry is sold by a time stop.

There is no cooldown after an exit: if the dip still qualifies on the
next bar, the bot buys again.

All decisions are exact integer arithmetic on the bar closes — no
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
