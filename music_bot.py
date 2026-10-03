
import os
import threading
import discord
from discord.ext import commands
import wavelink
from flask import Flask

# --- Keep-Alive Web Server for Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Dreamers Music Bot is online 24/7!", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
loop_modes = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    # Active public Lavalink nodes
    nodes = [
        wavelink.Node(
            identifier="Lavalink_Node1",
            uri="http://lavalink.proxy.lol:80",
            password="https://discord.gg/ajiekai"
        ),
        wavelink.Node(
            identifier="Lavalink_Node2",
            uri="http://ssl.lavalink.vcodes.xyz:443",
            password="youwon'tguessit"
        )
    ]
    await wavelink.Pool.connect(nodes=nodes, client=bot, cache_capacity=100)

@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print(f"Wavelink Node '{payload.node.identifier}' connected successfully!")

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    player: wavelink.Player = payload.player
    if not player:
        return

    guild_id = player.guild.id
    mode = loop_modes.get(guild_id, "none")

    if mode == "current" and payload.track:
        await player.play(payload.track)
        return
    elif mode == "queue" and payload.track:
        await player.queue.put_wait(payload.track)

    if not player.queue.is_empty:
        next_track = await player.queue.get_wait()
        await player.play(next_track)

# --- Music Commands ---

@bot.command(name="play", aliases=["p"])
async def play(ctx: commands.Context, *, search: str):
    if not ctx.author.voice:
        return await ctx.send("Join a voice channel first!")

    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    else:
        vc: wavelink.Player = ctx.voice_client

    tracks: wavelink.Search = await wavelink.Playable.search(search)
    if not tracks:
        return await ctx.send("No songs found.")

    if isinstance(tracks, wavelink.Playlist):
        added = await vc.queue.put_wait(tracks)
        await ctx.send(f"Added playlist **{tracks.name}** ({added} tracks) to queue!")
        if not vc.playing:
            await vc.play(vc.queue.get())
    else:
        track = tracks[0]
        if vc.playing:
            await vc.queue.put_wait(track)
            await ctx.send(f"Added to queue: **{track.title}**")
        else:
            await vc.play(track)
            await ctx.send(f"Now playing: **{track.title}**")

@bot.command(name="pause")
async def pause(ctx: commands.Context):
    vc: wavelink.Player = ctx.voice_client
    if vc and vc.playing:
        await vc.pause(True)
        await ctx.send("Paused playback.")

@bot.command(name="resume")
async def resume(ctx: commands.Context):
    vc: wavelink.Player = ctx.voice_client
    if vc and vc.paused:
        await vc.pause(False)
        await ctx.send("Resumed playback.")

@bot.command(name="skip", aliases=["s"])
async def skip(ctx: commands.Context):
    vc: wavelink.Player = ctx.voice_client
    if vc and vc.playing:
        await vc.skip(force=True)
        await ctx.send("Skipped!")

@bot.command(name="previous", aliases=["prev"])
async def previous(ctx: commands.Context):
    vc: wavelink.Player = ctx.voice_client
    if vc and vc.queue.history:
        prev_track = vc.queue.history.get()
        await vc.play(prev_track)
        await ctx.send(f"Playing previous: **{prev_track.title}**")
    else:
        await ctx.send("No previous track in history.")

@bot.command(name="loop")
async def loop(ctx: commands.Context, mode: str = None):
    guild_id = ctx.guild.id
    if not mode:
        return await ctx.send(f"Loop mode: **{loop_modes.get(guild_id, 'none')}**. Options: `off`, `track`, `queue`")

    mode = mode.lower()
    if mode in ["off", "none"]:
        loop_modes[guild_id] = "none"
        await ctx.send("Loop disabled.")
    elif mode in ["track", "song", "current"]:
        loop_modes[guild_id] = "current"
        await ctx.send("Looping current track.")
    elif mode in ["queue", "all"]:
        loop_modes[guild_id] = "queue"
        await ctx.send("Looping queue.")

@bot.command(name="stop", aliases=["dc", "leave"])
async def stop(ctx: commands.Context):
    vc: wavelink.Player = ctx.voice_client
    if vc:
        await vc.disconnect()
        await ctx.send("Disconnected.")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
