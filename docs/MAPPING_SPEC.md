# Kingmaker mapping spec — how a fair roll becomes a raid

One throne, one pot. A raid is a challenge against the throne-holder, resolved
by a single PTX roll. This document is the complete mapping from that roll to
the game outcome. It is published before the game runs, because the mapping —
not the roll — is where a game could cheat, and this one intends to be checked.

## The draw

Every raid is one PTX roll: `count=1`, range **1–10000**, `unique=false`, no
exclusions. The draw is uniform and quorum-signed; the game cannot bias it and
does not try.

## The outcome rule

**The challenger wins if and only if `result ≤ T`.**

`T` is the challenge threshold, in force at the moment the raid is dequeued,
and `P(win) = T / 10000`.

## The T-curve (season 1 constants)

```
T = clamp( 2000 + 12·B + 40·P , 2000 , 8500 )

B = blocks the current holder has held the throne
P = pot size in whole HMS
```

A fresh throne is defended at 80% (challenger 20%). Odds tilt toward the
challenger as tenure and pot grow, capping at 85% — the anti-domination
mechanism lives in the dice, not in a catch-up rule. **These constants are
fixed for the season.** They change only at a season boundary, announced in
advance; a mid-season change would invalidate the trust this document exists
to earn.

## The commitment

The threshold, the raid's sequence number and the raider's identity are
committed **into the signed round seed** via the roll's `game_id`:

```
km:s<season>:T=<T>:q=<seq>:p=<identity>
```

The chain folds `game_id` into the seed the quorum signs before any result
exists, so none of these values can be altered after the draw.

## Ordering

Raids resolve strictly one at a time, in sequence order. Your raid resolves
against whatever the throne is when your `q` is reached — if the raid before
yours took the throne, you are raiding the new holder, at the fresh-throne `T`
committed in *your* `game_id`. "Your roll won but someone confirmed first"
cannot happen here; the sequence is the order, and it is on chain.

## Verifying a raid — four steps, no trust required

1. **The roll is real:** open the raid's transaction at
   `https://ptx-explorer.lnky.uk/v2?q=<txid>` — the verifier re-derives the
   result from the quorum-signed beacon with no node.
2. **The terms were committed first:** read `game_id` in the payload — `T`,
   `q` and `p` are inside the signed seed, fixed before the result existed.
3. **The rule was applied:** check `result ≤ T` against the announced
   win/lose. One comparison.
4. **The order is intact:** `q` increases by one per raid; the season's full
   sequence reconstructs from the chain.

## What this proves, and what it does not

The chain proves the draw and the committed terms. It does not prove payment:
the binding between the identity label and a paid account is the rail's
attestation (see `PTXPAL_API.md`). A raid record proves *this draw, under
these terms, in this order* — the money side is auditable through the rail's
on-chain-deposits guarantee, not through the raid itself.
