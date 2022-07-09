from OSGDiscordBot import *
import discord
import subprocess
import paramiko
import asyncio
import re
from datetime import datetime


# execution block
if __name__ == '__main__':
  print("Opening SSH connection...")
  sshconnection = open_ssh_connection()

  print("Establishing connection to Discord...")
  intents = discord.Intents.default()
  intents.messages = True
  intents.members = True
  intents.guilds = True

  client = discord.Client(intents=intents)

  @client.event
  async def on_ready():
      print(f'Success! Logged in as {client.user}')

  @client.event
  async def on_custom_event():
    global sshconnection
    global status_message

    # Refresh SSH connection
    if sshconnection is not None:
      sshconnection.close()
      sshconnection = None
    sshconnection = open_ssh_connection()
    
    # Update status channel
    if STATUS_CHANNEL_ID is not None:
      outmsg = MSG_all_user_summaries(sshconnection, USERNAMES)
      if status_message is None:
        statuschannel = client.get_channel(STATUS_CHANNEL_ID)
        status_message = await statuschannel.send(outmsg)
      else:
        await status_message.edit(content=outmsg)

    # Update mobile-formatted channel
    if MOBILE_CHANNEL_ID is not None:
      outmsg = MSG_all_mobile_summaries(sshconnection, USERNAMES)
      if mobile_status_message is None:
        mobilechannel = client.get_channel(MOBILE_CHANNEL_ID)
        mobile_status_message = await mobilechannel.send(outmsg)
      else:
        print(mobilechannel)
        await mobile_status_message.edit(content=outmsg)

  @client.event
  async def on_message(message):
    RESPONSE_CHANNEL_ID = None
    if message.author == client.user:
      return

    if message.content.startswith('test'):
      rchannel = client.get_channel(995331833610895382)
      newmsg = rchannel.last_message_id
      print(newmsg)
      return

    if not message.content.startswith('!'):
      return
    

    global notif_list
    print(notif_list)
    ipt = message.content[1:]
    print(ipt) 
   # dedicated response channel if requested
    rchannel = client.get_channel(RESPONSE_CHANNEL_ID) if RESPONSE_CHANNEL_ID is not None else message.channel
    if ipt == 'all':
      outmsg = MSG_all_user_summaries(sshconnection, USERNAMES)

    ## HELP MESSAGE
    elif ipt == 'h' or ipt == 'help':
      outmsg = MSG_help_str()
    
    ## FORCE UPDATE
    elif ipt == 'update':
      await message.add_reaction(THUMBS_UP_EMOJI)
      client.dispatch("custom_event")
      return
    
    ## SET UPDATE TIMER
    elif ipt.startswith('setupdatetimer'):
      ipt = ipt.split()
      if len(ipt) != 2:
        outmsg = "Please specify a time using `!setupdatetime <integer>`. Thanks!"
        await message.channel.send(outmsg)
        return
      ipt = ipt[1]
      if not ipt.isdigit() or int(ipt) < 10:
        outmsg = "Update time must be a positive integer at least 10."
        await message.channel.send(outmsg)
        return
      else:
        global STATUS_REFRESH_TIME
        STATUS_REFRESH_TIME = int(ipt)
        outmsg = "Refresh time set to " + ipt + " second(s). This will take effect after the next update."
        await message.channel.send(outmsg)
        return
    
    ## SET NOTIFICATIONS
    elif ipt.startswith('notifyme') or ipt.startswith('unnotifyme'):
      ipt = ipt.split()
      if ipt[0].startswith('notifyme'):
        addnotif = True
        strerr = "Please specify a username with `!notifyme <username>`. Thanks!"
      else:
        addnotif = False
        strerr = "Please specify a username with `!unnotifyme <username>`. Thanks!"
      if len(ipt) != 2:
        await message.channel.send(strerr)
        return
      ipt = ipt[1]
      if ipt not in USERNAMES:
        await message.channel.send("Error: I can't find that username!")
        return
      else:
#          global notif_list
        username = ipt
        sender = message.author
        curlist = notif_list[ipt]
        if sender in curlist and addnotif:
          outmsg = "You're already being notified of `" + username + "`'s updates."
          await message.chanel.send(outmsg)
          return
        elif sender not in curlist and not addnotif:
          outmsg = "You're not being notified of `" + username + "`'s updates."
          await message.chanel.send(outmsg)
          return
        elif addnotif:
          curlist.append(sender)
          outmsg = "Got it, I'll notify you of `" + username + "`'s updates."
        else:
          curlist.remove(sender)
          outmsg = "Got it, I'll stop notifying you of `" + username + "`'s updates."
        notif_list[ipt] = curlist
        await message.channel.send(outmsg)
        return

    ## RESPOND TO MESSAGES
    else:
      return
      mostrecent = False
      alljobs = False
      if ipt.startswith('!'):
        mostrecent = True
        ipt = ipt[1:]
      elif ipt.startswith('job'):
        alljobs = True
        ipt = ipt.split()
        if len(ipt) != 2:
          outmsg = "Please specify a username using `!job <username>`. Thanks!"
          # Corrections to commands will always be sent in-context
          await message.channel.send(outmsg)
          return
        ipt = ipt[1]

      if ipt in USERNAMES:
        if mostrecent:
          outmsg = MSG_most_recent_job(sshconnection, ipt)
        elif alljobs:
          outmsg = MSG_all_user_jobs(sshconnection, ipt)
        else:
          outmsg = MSG_all_user_summaries(sshconnection, [ipt])
      else:
        outmsg = "Error: username `" + ipt + "` is not allowed to be queried."
    await rchannel.send(outmsg) 


  client.run(DISCORD_TOKEN)


