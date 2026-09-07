# PTXPal API — the public contract

PTXPal sells verifiable PTX rolls. A consumer (this game, a gaming platform,
anything) tops an identity up with an on-chain HMS deposit, receives **rolls**
— entitlements to play, a count — and spends them one request at a time over
HTTPS with an API key. The base URL and key are issued out of band.

**Everything in this document is intended-public. Nothing about PTXPal outside
this document appears in this repository, by policy.**

## The model: rolls held, not money held

This is the arcade-token model, and it is a guarantee, not a framing. HMS sent
to a deposit address **belongs to the operator the moment it arrives**, in
exchange for rolls at the app's posted rate. What an identity holds is an
entitlement to play — *"8 raids remaining"*, never *"8 HMS"*. **There is no
withdrawal endpoint, no refund path in the API, and no user balance
denominated in money anywhere in the rail.** Entitlements are non-refundable
and may expire per an app's published policy.

## Guarantees

1. **All inbound value is on-chain.** The only way rolls are created is a
   visible HMS transaction to your deposit address, converted at the app's
   posted rate. There are no off-chain credits, no admin grants, no transfers
   between identities. Every roll-count is therefore reconcilable against the
   public chain, and a discrepancy is externally detectable.
2. **The rail owns the roll shape.** Every roll is `count=1, unique=false, no
   excludes`, over a range fixed per app. The one PTX failure mode that
   charges a fee without returning a result is unreachable by construction —
   no customer input can trigger it.
3. **Idempotency.** `request_id` is unique per app: a replay returns the
   original result and never double-spends a roll. Deposits credit once per
   `(txid, vout)`, ever. A deposit credits `floor(amount / rate)` rolls; a
   sub-rate remainder accumulates on the account and converts when it reaches
   a whole roll.
4. **Ordering is committed.** Each roll gets a strictly-increasing sequence
   number at dequeue, folded into the `game_id` the quorum signs. The order
   the rail served is provable after the fact; fairness of *arrival* ordering
   is the rail's attestation.
5. **Credit timing is per app**: `credit_on = seen | confirmed`. Under `seen`,
   a top-up credits rolls when the transaction is observed, before it
   confirms — near-instant funding.

## Zero-conf crediting: the stated risk

Under `credit_on = seen`, a deposit that is double-spent or dropped before
confirming has credited rolls that were never paid for. Because rolls are
entitlements and no withdrawal exists, those phantom rolls can only be
*played*: the entire exposure is the on-chain roll fees they burn before the
next reconciliation notices the deposit vanished — single-digit HMS. There is
no path by which a phantom deposit extracts money, because no path extracts
money. Apps that want zero exposure run `credit_on=confirmed`.

## Endpoints

Auth: `X-PTXPal-Key: <api key>` on every request. All bodies JSON.

### POST /v1/roll
```json
{ "request_id": "uuid", "identity": "discord:123456789012345678", "tag": "s1:T=6350" }
```
→ `200`
```json
{ "seq": 417, "roll_txid": "…", "results": [4211],
  "game_id": "km:s1:T=6350:q=417:p=discord:123456789012345678" }
```
Synchronous — the PTX roll returns in under a second. `tag` is the caller's
free segment (game semantics live here); the rail injects `q=<seq>` and
`p=<identity>`. Total `game_id` must fit the chain's 128-byte cap; the rail
rejects a `tag` that would overflow it.

Errors: `402` no rolls remaining · `409` duplicate `request_id` (body carries
the original result) · `503` no rolls currently serviceable (see
availability — nothing was deducted).

### GET /v1/rolls/{identity}
→ `{ "rolls": 8 }` — rolls remaining. A count, not a currency.

### POST /v1/deposit-address
`{ "identity": "…" }` → `{ "address": "y…", "rate": "1 HMS = 1 roll" }` —
stable per identity. Sending here is the top-up: one deposit, N rolls, then
every play is instant.

### GET /v1/availability
→ `{ "rolls_available": 14 }` — how many rolls the rail can serve right now.
Consumers should surface this and refuse to sell an action when it is 0; a
request sent anyway fails `503` with no deduction.

## What the chain proves, and what PTXPal attests

The chain proves the draw: the results follow from a quorum-signed beacon, and
the `game_id` — including the sequence number, the identity label and the
caller's tag — was committed into the signed seed *before the result existed*.
Anyone can verify this with no node, at the public verifier.

PTXPal attests the rest: that the identity in the label is the account that
topped up, and that requests were dequeued in arrival order. `game_id` labels
the roll; it does not prove payment. That distinction is stated here so no one
has to discover it.
