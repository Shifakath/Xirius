import discord
from discord.ext import commands
import yt_dlp
from youtubesearchpython import VideosSearch
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True

# Set bot prefix
bot = commands.Bot(command_prefix="!", intents=intents)

# Music queue to handle songs
music_queue = []
is_playing = False
current_song = None
voice_channel = None

# Default volume
current_volume = 0.5

# Create a folder for audio files if it doesn't exist
if not os.path.exists("audio"):
    os.mkdir("audio")


# Tell bot when it's ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


# Function to search for a song on YouTube and get the URL
def search_youtube(query):
    videos_search = VideosSearch(query, limit=1)
    result = videos_search.result()
    video_url = result['result'][0]['link']
    video_title = result['result'][0]['title']
    return video_url, video_title


# Join a voice channel
@bot.command()
async def join(ctx):
    global voice_channel
    if ctx.author.voice:
        voice_channel = ctx.author.voice.channel
        await voice_channel.connect()
    else:
        await ctx.send("You need to be in a voice channel to use this command.")


# Leave the voice channel
@bot.command()
async def leave(ctx):
    global voice_channel
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        voice_channel = None
        await ctx.send("Disconnected.")
    else:
        await ctx.send("I'm not in a voice channel.")


# Function to play next song in the queue
async def play_next(ctx):
    global is_playing, current_song

    if len(music_queue) > 0:
        is_playing = True
        current_song = music_queue.pop(0)

        url = current_song['url']
        title = current_song['title']

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'audio/%(title)s.%(ext)s',
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['formats'][0]['url']

        ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }

        voice_client = ctx.guild.voice_client
        if not voice_client.is_playing():
            voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=url2, **ffmpeg_opts), 
                              after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            voice_client.source = discord.PCMVolumeTransformer(voice_client.source)
            voice_client.source.volume = current_volume
            await ctx.send(f"Now playing: {title}")
        else:
            await ctx.send("Already playing a track.")
    else:
        is_playing = False
        current_song = None


# Play a song or add it to the queue
@bot.command()
async def play(ctx, *, query):
    global music_queue, is_playing

    if not ctx.voice_client:
        await join(ctx)

    url, title = search_youtube(query)
    song = {'url': url, 'title': title}
    music_queue.append(song)

    if not is_playing:
        await play_next(ctx)
    else:
        await ctx.send(f"Added to queue: {title}")


# Pause the current track
@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Paused the track.")
    else:
        await ctx.send("No music is playing.")


# Resume the current track
@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Resumed the track.")
    else:
        await ctx.send("The music is not paused.")


# Stop the current track and clear the queue
@bot.command()
async def stop(ctx):
    global music_queue, is_playing
    music_queue = []
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Stopped playing and cleared the queue.")
    else:
        await ctx.send("No music is playing.")
    is_playing = False


# Show the current queue
@bot.command()
async def queue(ctx):
    if len(music_queue) > 0:
        queue_list = "\n".join([song['title'] for song in music_queue])
        await ctx.send(f"Current queue:\n{queue_list}")
    else:
        await ctx.send("The queue is empty.")


# Adjust volume of the bot
@bot.command()
async def volume(ctx, volume: int):
    global current_volume
    if ctx.voice_client.is_playing():
        ctx.voice_client.source.volume = volume / 100
        current_volume = volume / 100
        await ctx.send(f"Volume set to {volume}%")
    else:
        await ctx.send("No music is playing to adjust the volume.")


# Skip the current track
@bot.command()
async def skip(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped the current song.")
        await play_next(ctx)
    else:
        await ctx.send("No music is playing.")


# Clear downloaded audio files
@bot.command()
async def clear(ctx):
    for file in os.listdir("audio"):
        file_path = os.path.join("audio", file)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            await ctx.send(f"Failed to delete {file}: {e}")
    await ctx.send("Cleared audio files.")


# Run the bot with your token
bot.run("MTI5ODI1OTY3MjkyMjQ2MDIyMg.Gem9iP.4zJdB34XoUQjr2v4-SOuxosseP9XuQ9QOMzaS4")
