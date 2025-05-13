import selfcord
import os
import yt_dlp
import asyncio
import subprocess
import colorama
import glob
colorama.just_fix_windows_console()

token = ""
ffmpeg_executable = r""

try:
    ffmpeg_detected = subprocess.run("ffmpeg", shell=False, capture_output=True, text=True)
    ffmpeg_detected = True
    ffmpeg_executable = "ffmpeg"
except FileNotFoundError:
    ffmpeg_detected = False

def makeconfig():
    global token
    global ffmpeg_executable
    global ffmpeg_detected
    if not bool(token):
        token = input("Please paste your user token here: ")
    if not ffmpeg_detected:
        ffmpeg_executable = input("ffmpeg not found. If it is installed, please paste the file path of ffmpeg here. Also note, yt_dlp may be buggy if ffmpeg is not in path: ") #this doesnt matter because yt_dlp uses ffmpeg and for yt_dlp it must be in PATH. too lazy to remove so its staying
    if not os.path.exists(os.path.expanduser("~/.selftune/config.txt")):
        with open(os.path.expanduser("~/.selftune/config.txt"), "w") as file:
            file.write(f"{token}\n")
            file.write(ffmpeg_executable)

def useconfig():
    global token
    global ffmpeg_executable
    with open(os.path.expanduser("~/.selftune/config.txt"), "r") as file:
        lines = file.readlines()
        token = lines[0].strip()
        ffmpeg_executable = lines[1].strip()

if os.path.exists(os.path.expanduser("~/.selftune/config.txt")):
    useconfig()
if not token or not ffmpeg_executable:
    makeconfig()

if not os.path.exists(os.path.expanduser("~/.selftune")):
    os.makedirs(os.path.expanduser("~/.selftune"))
os.chdir(os.path.expanduser("~/.selftune"))

ydl_opts = {
    'format': 'm4a/bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3'
    }]
}

music_playing = False
loop = False
loopq = False
global music_queue
music_queue = {}
loopq_to_play = 1

async def download_video(url, ydl_opts):
    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info_dict)
            filename = filename.rsplit('.', 1)[0] + '.mp3'
            ydl.download([url])
            return filename
    return await asyncio.to_thread(_download)


def get_first_playlist_item_link(playlist_url):
    playlist_opts = {
        'playlist_items': '1',
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(playlist_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        if info and 'entries' in info and len(info['entries']) > 0:
            return info['entries'][0].get('url')
        else:
            return None

async def download_playlist(url, ydl_opts, rest=bool):
    async def _downloadplaylist():
        if rest == False:
            return await download_video(get_first_playlist_item_link(url), ydl_opts)
        else:
            playlist_opts = {
                'extract_flat': True,
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(playlist_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                filenames = []
                if info and 'entries' in info:
                    for entry in info['entries']:
                        video_url = entry.get('url')
                        if video_url:
                            filename = await download_video(video_url, ydl_opts)
                            filenames.append(filename)
                return filenames
    return await _downloadplaylist()



def log_command(command: str, username: str, userid: str, channelid: str):
    print(colorama.Fore.LIGHTBLUE_EX + command + colorama.Fore.YELLOW + " command invoked by " + colorama.Fore.GREEN + username + " (" + userid + ") " + colorama.Fore.YELLOW + "in channelID " + colorama.Fore.GREEN + channelid + colorama.Fore.RESET)

def get_current_voice_channel(client):
    if client.voice_clients and len(client.voice_clients) > 0:
        return client.voice_clients[0].channel
    return None

def reducequeue(queue):
    global music_queue
    music_queue = {i+1: song for i, song in enumerate(music_queue.values())}

def add_playlist_to_queue(filename):
    global music_queue
    position = max(music_queue) + 1 if music_queue else 1
    music_queue[position] = filename

class MyClient(selfcord.Client):
    def __init__(self):
        super().__init__()
        self.current_voice = None
        
    async def on_ready(self):
        print('Logged on as', self.user)
        await self.change_presence(activity=selfcord.Activity(type=selfcord.ActivityType.playing, name="type $help for music"))
    
    async def download_and_queue_rest(self, url, ydl_opts):
        try:
            if not os.path.exists(os.path.expanduser("~/.selftune/playlist")):
                os.mkdir(os.path.expanduser("~/.selftune/playlist"))
            os.chdir(os.path.expanduser("~/.selftune/playlist"))
            
            #delete all prior songs
            for filename in glob.glob(os.path.join(os.path.expanduser("~/.selftune/playlist"), "*.mp3")):
                if os.path.isfile(filename):
                    os.remove(filename)
            
            #download the songs in this folder to prevent exceptions of the first song file in use error
            filenames = await download_playlist(url, ydl_opts, rest=True)
            dont_queue_first_song = 0
            for fn in filenames:
                dont_queue_first_song = dont_queue_first_song + 1
                if dont_queue_first_song != 1:
                    add_playlist_to_queue(fn)
            
            #move the songs back to the original folder
            try:
                for filename in os.listdir(os.path.expanduser("~/.selftune/playlist")):
                    #not gonna use shutil or os because its bad at overwriting files
                    #just realized this is a useless for loop because i was originally gonna use shutil and that needed a for loop but xcopy and cp doesnt need one and i needa stop yappng oh my gyat rizz
                    if os.name == "nt":
                        os.system("xcopy /s /y * ..\\")
                        break
                    if os.name == "posix":
                        os.system("cp * ../")
                        break

            except PermissionError as e:
                pass
            os.chdir(os.path.expanduser("~/.selftune/"))
        except Exception as e:
            print("Error downloading rest of playlist:" + str(e))
            os.chdir(os.path.expanduser("~/.selftune/"))

    async def on_message(self, message):
        global loop
        global music_queue
        global loopq_to_play
        global loopq

        if message.content == "$help":
            log_command("$help", message.author.name, str(message.author.id), str(message.channel.id))
            help_message = (
                "[SelfTune by Greenishes](<https://github.com/Greenishess/selftune>)\n"
                "Version: **3.1.0**\n"
                "Commands:\n"
                "**$ping** - Check the bot's latency\n"
                "**$play <youtube video or playlist url>** - Play a song or playlist from YouTube (playlist functionality is in beta, dont count on it working)\n"
                "**$stop** - Stop playing and disconnect from the voice channel\n"
                "**$viewqueue** - View the current queue\n"
                "**$viewq** - Alias for $viewqueue\n"
                "**$loop** - Loop the current song\n"
                "**$skip** - Skip the current song\n"
                "**$loopqueue** - Loops the queue\n"
                "**$loopq** - Alias for $loopqueue\n"
                "**$clearqueue** - Clears the queue\n"
                "**$clearq** - Alias for $clearqueue\n"
                f"Status: Loop: {loop} Loop queue: {loopq} Posistion in queue: {loopq_to_play}"

            )
            await message.channel.send(help_message, silent=True)

        elif message.content == '$ping':
            log_command("$ping", message.author.name, str(message.author.id), str(message.channel.id))
            await message.channel.send('Pong! (' + str(self.latency * 1000) + "ms)")

        elif message.content.startswith("$echo"):
            log_command("$echo", message.author.name, str(message.author.id), str(message.channel.id))
            args = message.content[6:]
            if args.strip() == "":
                await message.channel.send("You didn't say anything to echo...")
            else:
                await message.channel.send(args.strip())

        elif message.content.startswith("$play"):
            log_command("$play", message.author.name, str(message.author.id), str(message.channel.id))
            args = message.content[6:]
            channel = message.author.voice.channel if message.author.voice else None
            if channel is None:
                return

            current_channel = get_current_voice_channel(self)
            voice_connection = None

            if current_channel is not None:
                if current_channel == channel:
                    voice_connection = self.voice_clients[0]
                else:
                    await self.voice_clients[0].disconnect()
                    try:
                        voice_connection = await channel.connect(ring=False)
                    except TypeError:
                        voice_connection = await channel.connect()
            else:
                try:
                    try:
                        voice_connection = await channel.connect(ring=False)
                    except TypeError:
                        voice_connection = await channel.connect()
                except selfcord.ClientException:
                    if message.guild.voice_client:
                        await message.guild.voice_client.disconnect()
                    try:
                        voice_connection = await channel.connect(ring=False)
                    except TypeError:
                        voice_connection = await channel.connect()

            self.current_voice = voice_connection

            if args.strip() == "":
                await message.channel.send("Usage: **$play <youtube url>**")
                return

            try:
                if "<" in args and ">" in args:
                    args = args.strip().split("<")[1].split(">")[0]

                if not self.current_voice.is_playing():
                    await message.channel.send("**Downloading, please wait...**", silent=True)
                else:
                    addingmsg = await message.channel.send("**Adding...**", silent=True)

                is_playlist = "playlist" in args or "list=" in args

                if is_playlist:
                    #if its a playlist, download the first song then play it, and download the rest of the songs in the playlist while the song is playing
                    filename = await download_playlist(args.strip(), ydl_opts, rest=False)

                else:
                    filename = await download_video(args.strip(), ydl_opts)

                try:
                    self.current_voice.play(selfcord.FFmpegPCMAudio(executable=ffmpeg_executable, source=filename))
                    await message.channel.send(f"Playing: **{filename}**", silent=True)
                    if is_playlist:
                        asyncio.create_task(self.download_and_queue_rest(args.strip(), ydl_opts))

                    if loopq and not music_queue:
                        music_queue[1] = filename

                    while 1:
                        await asyncio.sleep(1)
                        if loop:
                            if not self.current_voice.is_playing():
                                self.current_voice.play(selfcord.FFmpegPCMAudio(executable=ffmpeg_executable, source=filename))
                        else:
                            if not self.current_voice.is_playing():
                                if music_queue:
                                    if not loopq:
                                        position = min(music_queue)
                                        filename = music_queue[position]
                                    else:
                                        try:
                                            filename = music_queue[loopq_to_play]
                                            loopq_to_play += 1
                                        except:
                                            loopq_to_play = 1
                                            filename = music_queue[loopq_to_play]

                                    self.current_voice.play(selfcord.FFmpegPCMAudio(executable=ffmpeg_executable, source=filename))
                                    if not loopq:
                                        del music_queue[position]
                                        reducequeue(music_queue)
                                else:
                                    return
                except selfcord.errors.ClientException:
                    position = max(music_queue) + 1 if music_queue else 1
                    music_queue[position] = filename
                    if addingmsg:
                        try:
                            await addingmsg.edit(f"**Added to queue:** {filename}")
                        except UnboundLocalError as e:
                            pass #for some reason if addingmsg doesnt work to check if addingmsg has value to it, and if it doesnt have value a harmless error will be sent
                    else:
                        await message.channel.send(f"**Added to queue:** {filename}", silent=True)

            except AttributeError as e:
                pass #prevents nonetype harmless error from being sent

            except Exception as e:
                await message.channel.send(f"**Error:** {e}", silent=True)

        elif message.content == "$stop":
            log_command("$stop", message.author.name, str(message.author.id), str(message.channel.id))
            try:
                if self.current_voice is not None:
                    await self.current_voice.disconnect()
                    self.current_voice = None
                    await message.channel.send("Disconnected", silent=True)
                    music_queue = {}
            except AttributeError:
                pass #because we stop playing it before we disconnect, it will send a harmless error saying is_playing is false so we'll pass that
            except Exception as e:
                await message.channel.send("**Error:** " + str(e), silent=True)

        elif message.content in ["$viewqueue", "$viewq"]:
            log_command("$viewqueue", message.author.name, str(message.author.id), str(message.channel.id))
            if music_queue:
                pretty_queue = "\n".join(f"{i}. {name.removesuffix('.mp3')}" for i, name in music_queue.items())
            else:
                pretty_queue = "The queue is empty! Try queuing some songs!"
            try:
                await message.channel.send(pretty_queue, silent=True)
            except selfcord.errors.HTTPException:
                try:
                    await message.channel.send(music_queue, silent=True)
                except selfcord.errors.HTTPException:
                    await message.channel.send("Why is your queue so big? It's **over the maximum amount of characters you can send** in a Discord message!")

        elif message.content == "$loop":
            log_command("$loop", message.author.name, str(message.author.id), str(message.channel.id))
            loop = not loop
            await message.channel.send("Looping the current song" if loop else "Stopped looping the current song", silent=True)

        elif message.content in ["$loopq", "$loopqueue"]:
            log_command("$loopqueue", message.author.name, str(message.author.id), str(message.channel.id))
            loopq = not loopq
            await message.channel.send("Looping the current queue" if loopq else "Stopped looping the current queue", silent=True)

        elif message.content == "$skip":
            log_command("$skip", message.author.name, str(message.author.id), str(message.channel.id))
            if self.current_voice is not None:
                if music_queue:
                    if loopq:
                        loopq_to_play += 1
                        if loopq_to_play > len(music_queue):
                            loopq_to_play = 1
                        filename = music_queue[loopq_to_play]
                        self.current_voice.stop()
                        await message.channel.send(f"Skipped to **{filename}**", silent=True)
                        self.current_voice.play(selfcord.FFmpegPCMAudio(executable=ffmpeg_executable, source=filename))
                    else:
                        position = min(music_queue)
                        filename = music_queue[position]
                        self.current_voice.stop()
                        await message.channel.send(f"Skipped to **{filename}**", silent=True)
                        self.current_voice.play(selfcord.FFmpegPCMAudio(executable=ffmpeg_executable, source=filename))
                        del music_queue[position]
                        if music_queue:
                            reducequeue(queue=music_queue)
                else:
                    await message.channel.send("No songs in queue", silent=True)

        elif message.content in ["$clearqueue", "$clearq"]:
            log_command("$clearqueue", message.author.name, str(message.author.id), str(message.channel.id))
            music_queue = {}
            await message.channel.send("**Cleared the queue**", silent=True)


client = MyClient()
client.run(token)
