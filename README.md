# OSGDiscordStatus
Bot to check status of jobs on OSG, and then send update messages.

Before running, run `./install.sh`. This will install dependencies and generate a template 
credentials file called `CREDENTIALS.py`. The credentials file is just a text file containing 
constants necessary for operation of the bot. Make sure to fill in this file before running 
the main script, `OSGDiscordBot.py`. You'll also need to make sure you've added the bot to your
Discord server. You can find more information about making Discord bots and adding them to servers in [the discord.py reference manual](https://discordpy.readthedocs.io/en/stable/discord.html).

In order for your bot to work, you'll need a bot token. If you're not sure where to find this, check out
[this link](https://www.writebots.com/discord-bot-token/#:~:text=A%20Discord%20Bot%20Token%20is,Discord%20Bot%20Token%20with%20anyone.).
Make sure to add this token to your `CREDENTIALS.py` file.

You'll also need a discord server to add the bot to. Once you've created a server, you'll have to specify a channel for the bot to post its 
regular updates. From within discord, you can find the ID for a given channel by right-clicking the channel name on the left bar and clicking "Copy ID".
This should be am 18 digit code, which you can paste into `CREDENTIALS.py`.

This also includes a file `OSGDiscordBot.service`, in case you want to run this as a service on
Linux distributions. To execute this, first edit the `OSGDiscordBot.service` file to replace
`USERNAME` with your username and all directories/paths with the correct values, then run the following:

```
cp OSGDiscordBot.service /lib/systemd/system/OSGDiscordBot.service
sudo systemctl daemon-reload
sudo systemctl enable OSGDiscordBot.service
sudo systemctl start OSGDiscordBot.service
```
