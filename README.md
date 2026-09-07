# PTX-Kingmaker

A Discord game built on the Hemis PTX beacon: one throne, one pot, raids
resolved by verifiable on-chain rolls. This repository is public because the
game is a worked example of consuming the beacon — every raid links to a
transaction anyone can verify with no node.

Three services, distinct jobs: **PeteX** answers operator questions
(corpus-only), **PTXPal** holds credit and spends rolls (custodial rail,
private), **PTX-Kingmaker** (this repo) is the game — a thin front end of
PTXPal's public API.

Start with:
- [`docs/MAPPING_SPEC.md`](docs/MAPPING_SPEC.md) — how a fair roll becomes a raid, and how to check it
- [`docs/PTXPAL_API.md`](docs/PTXPAL_API.md) — the rail's public contract

Nothing about PTXPal beyond its public API appears in this repository, by
policy.
