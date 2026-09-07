#!/usr/bin/env python3
"""PTX-Kingmaker Discord front end. Commands in one channel; every raid posts
its result instantly and its verification link as corroboration -- the link is
never a gate the player waits behind.

Secrets (Discord token) come from the environment file the unit reads; the
rail's URL and key likewise. Nothing here knows how the rail holds money.
"""
import os, discord, engine

CHANNEL = int(os.environ["KM_CHANNEL_ID"])
TOKEN   = os.environ["KM_DISCORD_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def fmt_s(s):
    h, m = divmod(s // 60, 60)
    return "%dh %02dm" % (h, m) if h else "%dm %02ds" % (m, s % 60)

HELP = ("**Kingmaker** — one throne, one pot.\n"
        "`!raid` challenge the throne (one roll, verifiable) · `!throne` status · "
        "`!pot` the pot · `!take` bank the pot and abandon the throne · "
        "`!top` leaderboard (time on throne) · `!help` this")

@client.event
async def on_ready():
    print("kingmaker connected as %s" % client.user, flush=True)

@client.event
async def on_message(msg):
    if msg.author.bot or msg.channel.id != CHANNEL:
        return
    text = msg.content.strip().lower()
    ident = "discord:%d" % msg.author.id
    name = msg.author.display_name
    if text == "!help":
        await msg.channel.send(HELP)
    elif text == "!throne":
        s = engine.status()
        if s["holder"]:
            await msg.channel.send("👑 **%s** holds the throne (for %s). Pot: **%d**. "
                                   "Next raid succeeds on ≤ **%d**/%d (%.1f%%)."
                                   % (s["holder"].split(":")[-1], fmt_s(s["held_for_s"]),
                                      s["pot"], s["T_next_raid"], engine.N,
                                      100.0 * s["T_next_raid"] / engine.N))
        else:
            await msg.channel.send("The throne is **empty** — `!raid` claims it outright "
                                   "(still one committed roll). Pot: **%d**." % s["pot"])
    elif text == "!pot":
        await msg.channel.send("The pot holds **%d**. Taking it costs the throne." %
                               engine.status()["pot"])
    elif text == "!take":
        r = engine.take_pot(ident)
        await msg.channel.send(("💰 **%s** banks a pot of **%d** and abandons the throne!"
                                % (name, r["banked"])) if r["ok"] else
                               ("%s — %s" % (name, r["error"])))
    elif text == "!top":
        rows = engine.leaderboard()
        if not rows:
            await msg.channel.send("Nobody has held the throne yet this season.")
            return
        lines = ["**Season %s — time on throne**" % engine.status()["season"]]
        for i, p in enumerate(rows, 1):
            lines.append("%d. %s — %s · %d raids · %d wins · %d banked"
                         % (i, p["identity"].split(":")[-1], fmt_s(p["tenure_s"]),
                            p["raids"], p["wins"], p["pots_banked"]))
        await msg.channel.send("\n".join(lines))
    elif text == "!raid":
        r = engine.raid(ident)
        if not r["ok"]:
            await msg.channel.send("⚔️ %s — raid refused: %s" % (name, r["error"]))
            return
        if r["win"]:
            deth = (" **%s is dethroned!**" % r["dethroned"].split(":")[-1]) if r["dethroned"] else ""
            await msg.channel.send("⚔️ **%s rolls %d ≤ %d — TAKES THE THRONE!**%s\n"
                                   "roll `q=%d` · verify: %s"
                                   % (name, r["result"], r["T"], deth, r["seq"], r["verify"]))
        else:
            await msg.channel.send("⚔️ %s rolls **%d** > %d — repelled. The pot grows to **%d**.\n"
                                   "roll `q=%d` · verify: %s"
                                   % (name, r["result"], r["T"], r["pot"], r["seq"], r["verify"]))

engine.init()
client.run(TOKEN, log_handler=None)
