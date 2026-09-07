# PTXPal API — the public contract

PTXPal is a credit rail: it holds a balance for an external identity and spends
verifiable PTX rolls on that identity's request. A consumer (this game, a
gaming platform, anything) talks to it over HTTPS with an API key. The base URL
and key are issued out of band.

**Everything in this document is intended-public. Nothing about PTXPal outside
this document appears in this repository, by policy.**

## Guarantees

These are guarantees of the service, not implementation notes.

1. **All inbound value is on-chain.** The only way credit is created is a
   visible HMS transaction to your deposit address. There are no off-chain
   top-ups, no admin credits, no transfers between identities. Every credit is
   therefore reconcilable against the public chain, and a ledger discrepancy is
   externally detectable.
2. **The rail owns the roll shape.** Every roll is `count=1, unique=false, no
   excludes`, over a range fixed per app at registration. The one PTX failure
   mode that charges a fee without returning a result (`pool too small for
   unique draw`) is unreachable by construction — no customer input can
   trigger it.
3. **Idempotency.** `request_id` is unique per app: a replay returns the
   original result and never double-debits or double-rolls. Deposits credit
   once per `(txid, vout)`, ever.
4. **Ordering is committed.** Each roll is assigned a strictly-increasing
   sequence number at the moment it is dequeued, and that number is folded into
   the `game_id` the quorum signs. The order the rail served is therefore
   provable after the fact. (Fairness of *arrival* ordering is the rail's
   attestation — see "what the chain proves".)
5. **Credit policy is per app**: `credit_on = seen | confirmed`. Under `seen`,
   a deposit credits when the transaction is observed, before confirmation.
   **Withdrawals always require the backing deposit to be confirmed**,
   whichever policy is active — unconfirmed credit can be played, never
   withdrawn.

## Zero-conf crediting: the stated risk

Under `credit_on = seen`, a deposit transaction that is double-spent or dropped
before confirming has credited a balance that never arrives. Because
withdrawals require confirmed backing, that phantom credit can only be
*played*: the exposure per incident is the roll fees consumed before the next
reconciliation notices the deposit vanished — single-digit HMS in practice —
not the face value of the deposit. The deposit-sized worst case exists only if
the withdrawal gate were removed, which is why it is a guarantee above rather
than a setting. Apps that prefer no exposure at all run `credit_on=confirmed`.

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

Errors: `402` insufficient credit · `409` duplicate `request_id` (body carries
the original result) · `503` no rolls currently available (see availability —
nothing was debited).

### GET /v1/balance/{identity}
→ `{ "balance": "12.00000000", "playable": "12.00000000", "withdrawable": "11.00000000" }`

### POST /v1/deposit-address
`{ "identity": "…" }` → `{ "address": "y…" }` — stable per identity.

### POST /v1/withdraw
`{ "request_id": "uuid", "identity": "…", "address": "y…", "amount": "5.0" }`
→ `{ "txid": "…" }`. Confirmed-backed credit only.

### GET /v1/availability
→ `{ "rolls_available": 14 }` — how many rolls the rail can serve right now.
Consumers should surface this and refuse to sell an action when it is 0; a
request sent anyway fails `503` with no debit.

## What the chain proves, and what PTXPal attests

The chain proves the draw: the results follow from a quorum-signed beacon, and
the `game_id` — including the sequence number, the identity label and the
caller's tag — was committed into the signed seed *before the result existed*.
Anyone can verify this with no node, at the public verifier.

PTXPal attests the rest: that the identity in the label is the account that
paid, and that requests were dequeued in arrival order. `game_id` labels the
roll; it does not prove payment. That distinction is stated here so no one has
to discover it.
