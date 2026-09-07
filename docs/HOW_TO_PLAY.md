# How to play Kingmaker

One throne, one pot. Time on the throne is the leaderboard; the pot is the
temptation to give it up. Every raid is decided by a real, quorum-signed
on-chain roll that anyone can verify — that is the whole point of the game.

## The commands

| command | what it does |
|---|---|
| `!raid` | challenge the throne — one roll decides it |
| `!throne` | who holds it, for how long, the pot, and the next raid's odds |
| `!pot` | the pot |
| `!take` | *holder only:* bank the pot — **and abandon the throne** |
| `!top` | leaderboard: time on throne this season |
| `!rules` | the short version of this page |

## The rules

- **A raid is one roll, 1–10000. You win if the roll is ≤ T.** `T` is shown by
  `!throne` before you raid, and is committed on-chain in your raid's
  `game_id` before the result exists — it cannot be changed after the fact.
- **T scales against the holder**: a fresh throne defends hard (challenger
  ~20%), and every block held and every point in the pot tilts the dice
  toward the challenger, up to 85%. Long reigns invite their own downfall.
- **A failed raid feeds the pot.** Win nothing, fatten the prize.
- **Taking the pot costs the throne.** The holder's dilemma: sit and build
  the tenure you are ranked on, or bank the pot and start again. Never both.
- **An empty throne is claimed, not contested** — the first `!raid` wins
  outright, still via a committed on-chain roll, so every reign starts
  verifiable.
- **Absence costs nothing.** Tenure accrues while you sleep; there is no
  defending action. The risk of holding is only that the dice tilt.
- **Seasons reset the board.** Tenure, pot and titles zero; the chain record
  of every past raid remains forever.

## Verifying a raid — trust nothing, check everything

Every raid the bot announces carries a link. Behind it, four checks anyone
can make with no node and no account (full detail: `MAPPING_SPEC.md`):

1. **The roll is real** — the verifier re-derives the result from the
   quorum's signature.
2. **The terms came first** — `T`, the sequence number and the raider are
   inside the signed seed, fixed before the draw.
3. **The rule was applied** — compare the result with `T` yourself.
4. **The order is intact** — sequence numbers reconstruct the whole season
   from the chain.

If the game ever cheated, the chain would convict it. That is the showcase.

## Funding: not yet, and here is the model

**Raids are currently free — this is the tuning season.** When real play
opens, funding works like arcade tokens (`PTXPAL_API.md`):

- You top up once with an on-chain HMS deposit to your personal address and
  receive **rolls** — a count of plays, at a posted rate.
- **Rolls are entitlements, not money.** The HMS is the house's on arrival;
  there is no balance, no withdrawal, no cashing out. You buy plays.
- Top-up is the only slow step (one confirmation-time wait); every raid after
  it is instant.

**Do not send HMS anywhere yet.** When deposits open it will be announced,
and the bot will hand you your address with `!deposit`.
