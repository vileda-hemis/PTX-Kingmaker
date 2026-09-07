#!/usr/bin/env python3
"""PTX-Kingmaker game engine. One throne, one pot, raids resolved by PTX rolls.

Thin front end of the PTXPal rail: everything financial happens behind five
HTTP endpoints (docs/PTXPAL_API.md). This engine holds GAME state only --
throne, tenure, pot, season -- in its own SQLite. The rail cannot see any of
it, and this code knows nothing about how the rail holds money.

The mapping is docs/MAPPING_SPEC.md, season-1 constants, and every raid's
terms (T, seq, raider) are committed into the quorum-signed round seed via
game_id before the result exists.
"""
import json, os, sqlite3, threading, time, urllib.request, uuid

RAIL_URL   = os.environ["PTXPAL_URL"]           # no default: issued out of band
RAIL_KEY   = os.environ["PTXPAL_KEY"]
DB         = os.environ.get("KM_DB", "/opt/kingmaker/kingmaker.db")
EXPLORER   = "https://ptx-explorer.lnky.uk"
# Season-1 constants, published in MAPPING_SPEC.md. Season-locked once real
# players are in; tuned only during the notional phase.
T_BASE, T_PER_BLOCK, T_PER_POT, T_MIN, T_MAX = 2000, 12, 40, 2000, 8500
N = 10000
RAID_COST_POT = 1        # a failed raid feeds the pot by its stake (notional units)

_lock = threading.Lock()  # raids resolve strictly one at a time, in seq order

def _rail(method, path, body=None):
    req = urllib.request.Request(RAIL_URL + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-PTXPal-Key": RAIL_KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

_height_cache = {"t": 0.0, "h": None}
def chain_height():
    """Public observe API, cached 30s; falls back to a 60s-spacing estimate so
    a verifier outage cannot stop the game. Public consumer, public endpoint --
    that is the point of the showcase."""
    now = time.time()
    if now - _height_cache["t"] < 30 and _height_cache["h"]:
        return _height_cache["h"]
    try:
        with urllib.request.urlopen(EXPLORER + "/v2/api/v1/observe/health", timeout=8) as r:
            h = json.load(r).get("height")
        if h:
            _height_cache.update(t=now, h=h)
            return h
    except Exception:
        pass
    if _height_cache["h"]:
        return _height_cache["h"] + int((now - _height_cache["t"]) // 60)
    return 0

def db():
    c = sqlite3.connect(DB, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    return c

def init():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS players(
      identity TEXT PRIMARY KEY, tenure_s INTEGER NOT NULL DEFAULT 0,
      raids INTEGER NOT NULL DEFAULT 0, wins INTEGER NOT NULL DEFAULT 0,
      pots_banked INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS raids(
      request_id TEXT PRIMARY KEY, identity TEXT, seq INTEGER, t INTEGER,
      result INTEGER, win INTEGER, roll_txid TEXT, game_id TEXT, ts INTEGER);
    INSERT OR IGNORE INTO state VALUES('season','1');
    INSERT OR IGNORE INTO state VALUES('pot','0');
    INSERT OR IGNORE INTO state VALUES('holder','');
    INSERT OR IGNORE INTO state VALUES('since','0');
    INSERT OR IGNORE INTO state VALUES('since_height','0');
    """)
    c.commit(); c.close()

def _get(c, k):  return c.execute("SELECT value FROM state WHERE key=?", (k,)).fetchone()[0]
def _set(c, k, v): c.execute("UPDATE state SET value=? WHERE key=?", (str(v), k))

def _accrue_holder(c, now):
    holder, since = _get(c, "holder"), int(_get(c, "since"))
    if holder and since:
        c.execute("INSERT INTO players(identity,tenure_s) VALUES(?,?) "
                  "ON CONFLICT(identity) DO UPDATE SET tenure_s=tenure_s+?",
                  (holder, now - since, now - since))
        _set(c, "since", now)

def current_T(c):
    holder = _get(c, "holder")
    if not holder:
        return N          # a vacant throne is claimed, not contested -- the roll
                          # still fires and commits, so every reign starts on-chain
    pot = int(_get(c, "pot"))
    b = max(0, chain_height() - int(_get(c, "since_height")))
    return max(T_MIN, min(T_MAX, T_BASE + T_PER_BLOCK * b + T_PER_POT * pot))

def _clean_name(name):
    """A display name safe to commit on-chain: [A-Za-z0-9_-], max 16 bytes.
    Empty result -> the by= field is simply omitted. Names are mutable, so the
    committed name is who they were at raid time -- the ID in p= remains the
    durable attribution."""
    import re as _re
    return _re.sub(r"[^A-Za-z0-9_-]", "", name or "")[:16]

def raid(identity, name=None):
    """One raid: commit T+seq+raider into a signed roll, apply the outcome."""
    with _lock:
        now = int(time.time())
        c = db()
        season = _get(c, "season")
        t = current_T(c)
        rid = "km-" + uuid.uuid4().hex[:20]
        n = _clean_name(name)
        tag = "s%s:T=%d" % (season, t) + ((":by=" + n) if n else "")
        code, r = _rail("POST", "/v1/roll",
                        {"request_id": rid, "identity": identity, "tag": tag})
        if code != 200:
            c.close()
            return {"ok": False, "error": r.get("error", "rail error %d" % code)}
        result, win = r["results"][0], r["results"][0] <= t
        prev = _get(c, "holder")
        _accrue_holder(c, now)
        c.execute("INSERT INTO players(identity,raids,wins) VALUES(?,1,?) "
                  "ON CONFLICT(identity) DO UPDATE SET raids=raids+1, wins=wins+?",
                  (identity, int(win), int(win)))
        if win:
            _set(c, "holder", identity); _set(c, "since", now)
            _set(c, "since_height", chain_height())
        else:
            _set(c, "pot", int(_get(c, "pot")) + RAID_COST_POT)
        c.execute("INSERT INTO raids VALUES(?,?,?,?,?,?,?,?,?)",
                  (rid, identity, r["seq"], t, result, int(win),
                   r["roll_txid"], r["game_id"], now))
        c.commit()
        out = {"ok": True, "win": win, "result": result, "T": t, "seq": r["seq"],
               "txid": r["roll_txid"], "game_id": r["game_id"],
               "dethroned": prev if (win and prev) else None,
               "pot": int(_get(c, "pot")),
               "verify": "%s/v2?q=%s" % (EXPLORER, r["roll_txid"])}
        c.close()
        return out

def take_pot(identity):
    """The holder's dilemma: bank the pot, abandon the throne."""
    with _lock:
        now = int(time.time())
        c = db()
        if _get(c, "holder") != identity:
            c.close(); return {"ok": False, "error": "you do not hold the throne"}
        pot = int(_get(c, "pot"))
        _accrue_holder(c, now)
        c.execute("UPDATE players SET pots_banked=pots_banked+? WHERE identity=?",
                  (pot, identity))
        _set(c, "holder", ""); _set(c, "since", 0); _set(c, "pot", 0)
        c.commit(); c.close()
        return {"ok": True, "banked": pot}

def status():
    c = db()
    now = int(time.time())
    holder, since = _get(c, "holder"), int(_get(c, "since"))
    s = {"season": _get(c, "season"), "holder": holder or None,
         "pot": int(_get(c, "pot")), "T_next_raid": current_T(c),
         "held_for_s": (now - since) if holder else 0, "reign_txid": None}
    if holder:
        # the winning raid that started the current reign -- its on-chain receipt
        r = c.execute("SELECT roll_txid FROM raids WHERE win=1 AND identity=? "
                      "ORDER BY seq DESC LIMIT 1", (holder,)).fetchone()
        if r: s["reign_txid"] = r[0]
    c.close(); return s

def leaderboard(limit=10):
    c = db()
    now = int(time.time())
    holder, since = _get(c, "holder"), int(_get(c, "since"))
    rows = c.execute("SELECT identity,tenure_s,raids,wins,pots_banked FROM players").fetchall()
    c.close()
    board = []
    for ident, ten, raids_, wins, banked in rows:
        if ident == holder and since:
            ten += now - since            # live tenure counts on the board
        board.append({"identity": ident, "tenure_s": ten, "raids": raids_,
                      "wins": wins, "pots_banked": banked})
    board.sort(key=lambda x: -x["tenure_s"])
    return board[:limit]

def reset_season():
    with _lock:
        c = db()
        new = int(_get(c, "season")) + 1
        c.execute("UPDATE players SET tenure_s=0, raids=0, wins=0, pots_banked=0")
        _set(c, "holder", ""); _set(c, "since", 0); _set(c, "pot", 0)
        _set(c, "season", new)
        c.commit(); c.close()
        return {"season": new}
