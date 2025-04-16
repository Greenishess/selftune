# SelfTune
SelfTune is a Discord self bot that plays music. Think of one of those normal music bots, but instead of running under a bot, this runs under a real account. Benefits include being able to play music in Discord groupchats, where you cannot add bots.
## commands
**$ping** - Check the bot's latency

**$play <youtube url>** - Play a song from YouTube

**$stop** - Stop playing and disconnect from the voice channel

**$viewqueue** - View the current queue

**$viewq** - Alias for $viewqueue

**$loop** - Loop the current song

**$skip** - Skip the current song

**$loopqueue** - Loops the queue

**$loopq** - Alias for $loopqueue

**$clearqueue** - Clears the queue

**$clearq** - Alias for $clearqueue



## how to install dependencies
```
# Linux/macOS
python3 -m pip install git+https://github.com/dolfies/discord.py-self@renamed#egg=selfcord.py[voice]

# Windows
py -3 -m pip install git+https://github.com/dolfies/discord.py-self@renamed#egg=selfcord.py[voice]
```
then, just `pip install yt-dlp` then you should be ready to run it
