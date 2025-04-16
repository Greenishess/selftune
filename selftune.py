import selfcord
import os
import yt_dlp
import asyncio
import subprocess

token = ""
ffmpeg_executable = r""


try: #detect if ffmpeg is installed to path and use that ffmpeg. if it's not, we're gonna ask the user for their ffmpeg path.
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
        ffmpeg_executable = input("ffmpeg not found. If it is installed, please paste the file path of ffmpeg here: ")
    if not os.path.exists(os.path.expanduser("~/.selftune/config.txt")):
        with open(os.path.expanduser("~/.selftune/config.txt"), "w") as file:
            file.write(f"{token}\n")
            file.write(ffmpeg_executable)

def useconfig():
    global token
    global ffmpeg_executable
    with open(os.path.expanduser("~/.selftune/config.txt"), "r") as file:
        lines = file.readlines()
        token = lines[0]
        ffmpeg_executable = lines[1]

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
    'postprocessors': [{  # Extract audio using ffmpeg
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

def get_current_voice_channel(client):
    if client.voice_clients and len(client.voice_clients) > 0:
        return client.voice_clients[0].channel
    return None

def reducequeue(queue):
    global music_queue
    music_queue = {i+1: song for i, song in enumerate(music_queue.values())}

class MyClient(selfcord.Client):
    def __init__(self):
        super().__init__()
        self.current_voice = None
        
    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        global loop
        global music_queue
        global loopq_to_play
        global loopq
        if message.content == "$help":
            print(f"help command invoked by {message.author.name} ({message.author.id})")
            help_message = (
                "Version: **1.4.0**\n"
                "Commands:\n"
                "**$ping** - Check the bot's latency\n"
                "**$play <youtube url>** - Play a song from YouTube\n"
                "**$stop** - Stop playing and disconnect from the voice channel\n"
                "**$viewqueue** - View the current queue\n"
                "**$viewq** - Alias for $viewqueue\n"
                "**$loop** - Loop the current song\n"
                "**$skip** - Skip the current song\n"
                "**$loopqueue** - Loops the queue\n"
                "**$loopq** - Alias for $loopqueue"
                "**$clearqueue** - Clears the queue\n"
                "**$clearq** - Alias for $clearqueue"
            )
            await message.channel.send(help_message, silent=True)
        
        
        
        if message.content == '$ping':
            print(f"ping command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
            await message.channel.send('Pong! (' + str(self.latency * 1000) + "ms)")
        
        
        
        
        elif message.content.startswith("$echo"):
            print(f"echo command invoked by {message.author.name} ({message.author.id})")
            args = message.content[6:]
            if args.strip() == "":
                await message.channel.send("You didn't say anything to echo...")
            else:
                await message.channel.send(args.strip())
                #made this to test command arguments
                
        
        
        
        elif message.content.startswith("$play"):
            print(f"play command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
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
                    voice_connection = await channel.connect(ring=False)
            else:
                try:
                    voice_connection = await channel.connect(ring=False)
                except selfcord.ClientException:
                    if message.guild.voice_client:
                        await message.guild.voice_client.disconnect()
                    voice_connection = await channel.connect(ring=False)
            
            #store the current voice connection
            self.current_voice = voice_connection
                    
            if args.strip() == "":
                await message.channel.send("Usage: **$play <youtube url>**")
            else:
                try:
                    if "<" and ">" in args.strip():
                        args = args.strip().split("<")[1].split(">")[0]
                    if not self.current_voice.is_playing():
                        await message.channel.send("**Downloading, please wait...**", silent=True)
                    if self.current_voice.is_playing():
                        confirmation_message = await message.channel.send("**Adding to the queue...**", silent=True)
                    filename = await download_video(args.strip(), ydl_opts)
                    self.current_voice.play(selfcord.FFmpegPCMAudio(executable=ffmpeg_executable, source=filename))

                    if loopq == True:
                        if not music_queue:
                            music_queue.update({1: filename})

                    await message.channel.send(f"Playing: **{filename}**", silent=True)
                    while 1:
                        await asyncio.sleep(1)
                        if loop == True:
                            if not self.current_voice.is_playing():
                                self.current_voice.play(selfcord.FFmpegPCMAudio(executable=ffmpeg_executable, source=filename))
                        else:
                            if not self.current_voice.is_playing():
                                if music_queue:
                                    if loopq == False:
                                        position = min(music_queue)
                                        filename = music_queue[position]
                                    if loopq == True:
                                        try:
                                            filename = music_queue[loopq_to_play]
                                            loopq_to_play = loopq_to_play + 1
                                        except Exception as e:
                                            loopq_to_play = 1
                                            filename = music_queue[loopq_to_play]
                                    self.current_voice.play(selfcord.FFmpegPCMAudio(executable=ffmpeg_executable, source=filename))
                                    if loopq == False:
                                        del music_queue[position]
                                    if music_queue:
                                        if loopq == False:
                                            reducequeue(queue=music_queue)
                                else:
                                    return
                except selfcord.errors.ClientException: #i was gonna use the music_playing variable to keep track if music is playing but i might just use this exception now instead
                    if music_queue:
                        position = max(music_queue) + 1
                        music_queue.update({position: filename})
                    else:
                        music_queue.update({1: filename})
                    await confirmation_message.edit(content=f"Added **{filename}** to the queue")
                except AttributeError:
                    pass #if you do $stop while a song is playing, it will send this error, so i just pass it since it doesn't matter
                except Exception as e:
                    await message.channel.send(f"**Error downloading:** {e}")



        elif message.content == "$stop":
            print(f"stop command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
            if self.current_voice is not None:
                await self.current_voice.disconnect()
                self.current_voice = None
                await message.channel.send("Disconected", silent=True)
            else:
                pass
        


        elif message.content == "$viewqueue":
            print(f"viewqueue command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
            await message.channel.send(music_queue, silent=True)



        elif message.content == "$viewq":
            print(f"viewq command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
            await message.channel.send(music_queue, silent=True)

        
        
        elif message.content == "$loop":
            print(f"loop command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
            if loop == False:
                loop = True
                await message.channel.send("Looping the current song", silent=True)
            else:
                loop = False
                await message.channel.send("Stopped looping the current song", silent=True)



        elif message.content == "$loopq":
            print(f"loopq command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
            if loopq == False:
                loopq = True
                await message.channel.send("Looping the current queue", silent=True)
            else:
                loopq = False
                await message.channel.send("Stopped looping the current queue", silent=True)


        elif message.content == "$loopqueue":
            print(f"loopq command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
            if loopq == False:
                loopq = True
                await message.channel.send("Looping the current queue", silent=True)
            else:
                loopq = False
                await message.channel.send("Stopped looping the current queue", silent=True)



        elif message.content == "$skip":
            print(f"skip command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
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
                    # Regular queue skip
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



        elif message.content == "$clearqueue":
            print(f"clearqueue command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
            music_queue = {}
            await message.channel.send("**Cleared the queue**", silent=True)



        elif message.content == "$clearq":
            print(f"clearq command invoked by {message.author.name} ({message.author.id}) in channelID {message.channel.id}")
            music_queue = {}
            await message.channel.send("**Cleared the queue**", silent=True)


client = MyClient()
client.run(token)
