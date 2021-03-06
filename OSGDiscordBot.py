import discord
from discord.ext import tasks
import subprocess
import paramiko
import asyncio
import re
from datetime import datetime
import CREDENTIALS

DISCORD_TOKEN = CREDENTIALS.DISCORD_BOT_TOKEN
OSGUSERNAME = CREDENTIALS.OSGLOGIN
OSGNODE = CREDENTIALS.OSGNODE
USERNAMES = CREDENTIALS.USERS_TO_CHECK
STATUS_REFRESH_TIME = CREDENTIALS.STATUS_REFRESH_TIME
SSH_REFRESH_TIME = CREDENTIALS.SSH_REFRESH_TIME
STATUS_CHANNEL_ID = CREDENTIALS.STATUS_CHANNEL_ID
MOBILE_CHANNEL_ID = CREDENTIALS.MOBILE_CHANNEL_ID
RESPONSE_CHANNEL_ID = CREDENTIALS.RESPONSE_CHANNEL_ID
HOLD_ALERT_RANGE = CREDENTIALS.HOLD_ALERT_RANGE

THUMBS_UP_EMOJI = '\N{THUMBS UP SIGN}'

lastupdate = [datetime.now() for i in range(len(USERNAMES))]
has_running_jobs = {user: False for user in USERNAMES}
has_running_update = {user: False for user in USERNAMES}
first_update = True

has_high_held_jobs = {user: False for user in USERNAMES}
has_alerted_held = {user: False for user in USERNAMES}


notif_list = {user: [] for user in USERNAMES}
ssh_reconnect = datetime.now()
sshconnection = None
status_task = None
ssh_task = None
#status_message = None
#mobile_status_message = None
update_ctr = 0


# Converts datestring from OSG to a datetime object
def datestring_to_datetime(dstr):
  year = datetime.now().year
  month = re.sub(r"^([0-9]{1,2})/.*", '\\1', dstr)
  if len(month) < 2:
    month = '0' + month
  day = re.sub(r"^.*/([0-9]{1,2}) .*", '\\1', dstr)
  if (len(day)) < 2:
    day = '0' + day

  newdstr = str(year) + ':' + month + ':' + day + ':' + dstr.split()[1]
  return(datetime.strptime(newdstr, '%Y:%m:%d:%H:%M'))

# Open ssh connection
def open_ssh_connection():
  k = paramiko.RSAKey.from_private_key_file(CREDENTIALS.PATH_TO_SSH_KEY, password=CREDENTIALS.SSHKEY_PWD)
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  print("- Connecting to host " + OSGNODE + " with username '" + OSGUSERNAME + "'...")
  client.connect(hostname=OSGNODE, username=OSGUSERNAME, pkey=k)
  print("- Connected to SSH!")

  return(client)

# Get status summary for all users
def MSG_all_user_summaries(client, usernames_lst):
  if client is None:
    return("Error: SSH Client not established.")
  formatstr = "{:>10} | {:>7} | {:>6} | {:>6} | {:>7} | {:>7}"
  totalmsg = '```\n' + formatstr.format("USERNAME", "DONE","RUN","IDLE","HELD","TOTAL") + '\n'
  totalmsg += '-'*(10 + 15 + 7 + 6 + 6 + 7 + 7) + '\n'
  for username in usernames_lst:
    totalmsg += MSG_user_summary(client, username, formatstr)
  totalmsg += '```\n'
  return(totalmsg)

# Gets status summary of all jobs for a given user
def MSG_user_summary(client, username, formatstr):
  if client is None:
    return("Error: SSH Client not established.")
  jobs, total = get_jobs_for_user(client, username)
  if len(username) > 9:
    username = username[:7] + '...'
  msg = formatstr.format(username, 
                        total['done'], 
                        total['run'], 
                        total['idle'], 
                        total['hold'], 
                        total['total'])
  msg += '\n'
  return(msg)

# Converts numbers to a smaller representation
#   used to truncate to human-readable amounts 
#   for mobile displays
def fmt_mobile_num(num, maxchar):
  suff = ['', 'K', 'M']
  val = float(num)
  for suffix in suff:
    if val < 1000:
      if suffix == '':
        return(str(int(val)))
      sufflen = len(suffix)
      vallen = len(str(int(val)))
      declen = max(maxchar-(sufflen+vallen+1), 0)
      fs = "{:" + str(vallen) + '.' + str(declen) + 'f}{}'
      return(fs.format(val, suffix))
    val /= 1000

def MSG_all_mobile_summaries(client, usernames_lst):
  # ios mobile has 32 characters total of width
  # I'm using 30 for a little buffer
  if client is None:
    return("Error: SSH Client not established.")
  formatstr = "{:>4} {:>4} {:>4} {:>4} {:>4} {:>5}"
  totalmsg = '```\n' + formatstr.format("USER","DONE","RUN","IDLE","HELD","TOTAL") + '\n'
  totalmsg += '-'*(30) + '\n'

  for username in usernames_lst:
    totalmsg += MSG_mobile_summary(client, username, formatstr)
  totalmsg += '```\n'
  return(totalmsg)

def MSG_mobile_summary(client, username, formatstr):
  if client is None:
    return("Error: SSH Client not established.")
  jobs, total = get_jobs_for_user(client, username)
  if len(username) > 3:
    username = username[:3]
  msg = formatstr.format(username, 
                        fmt_mobile_num(total['done'], 4), 
                        fmt_mobile_num(total['run'], 4), 
                        fmt_mobile_num(total['idle'], 4), 
                        fmt_mobile_num(total['hold'], 4), 
                        fmt_mobile_num(total['total'], 5))
  msg += '\n'
  return(msg)

# Gets all individual job status output for a particular user
def MSG_all_user_jobs(client, username):
  if client is None:
    return("Error: SSH Client not established.")
  jobs, total = get_jobs_for_user(client, username)
  outmsg = "Jobs for user `" + username + "`\n```\n"
  if (len(jobs) == 0):
    outmsg += 'No jobs found.'
  else:
    for i in range(len(jobs)):
      job = jobs[i]
      outmsg += jobentry_to_string(job, i+1)
  outmsg += '```\n'
  return(outmsg)

def MSG_help_str():
  stringhelp = '''
I can query OSG for the status of your jobs! 
Current commands:
  - `!all`             : Display summary of all lab members
  - `!username`        : Display summary for `username`
  - `!job username`    : Display status of all jobs for `username`
  - `!!username`       : Display status of most recent job for `username`
  - `!notifyme user`   : Ping me whenever job status changes for `user`
  - `!unnotifyme user` : Stop pinging me whenever job status changes for `user`
  - `!update`          : Force update of the status summary channel
  - `!help`            : Display this message

Only usernames allowed by the `CREDENTIALS` file can be queried.
Ask an admin to add your name to the list if you can't query yourself.
'''
  return(stringhelp)

# Converts dict of job to status string
def jobentry_to_string(jobentry, idx=None):
  formatstr = "{:>7} done, {:>5} running, {:>5} idle, {:>7} held, {:>7} total\n"
  jobstr =  formatstr.format(str(jobentry['done']),
                            str(jobentry['run']),
                            str(jobentry['idle']),
                            str(jobentry['hold']),
                            str(jobentry['total']))
  if idx is not None:
    jobstr = str(idx) + ') ' + jobstr
  return(jobstr)

# Get most string for most recent job for given user 
def MSG_most_recent_job(client, username):
  if client is None:
    return("Error: SSH Client not established.")
  jobs, total = get_jobs_for_user(client, username)
  outmsg = "Most recent job for user `" + username + '`'
  if (len(jobs) == 0):
    outmsg += '`\n```\nNo jobs found.'
  jobtimes = [datestring_to_datetime(job['submitted']) for job in jobs]
  most_recent = jobtimes.index(min(jobtimes))
  date = datestring_to_datetime(jobs[most_recent]['submitted'])
  datestr = date.strftime("%H:%M, %m/%d/%Y")
  outmsg += ', launched at ' + datestr + ':\n```\n'
  outmsg += jobentry_to_string(jobs[most_recent])
  outmsg += '```\n'
  return(outmsg)

# Generate a dictionary of jobs for a given user
def get_jobs_for_user(client, username):
  global has_running_update
  global has_high_held_jobs
  global has_alerted_held
  jobentry = {
    "batch_name": '',
    "submitted": '',
    "done": '0',
    "run": '0',
    "idle": '0',
    "hold": '0',
    "total": '0',
    "job_ids": ''
  }
  k = jobentry.keys()
  retval = []
  hasJobs = False

  command = 'condor_q ' + username
  stdin, stdout, stderr = client.exec_command(command)
  
  rawstring = str(stdout.read())
  resspl = [i for i in rawstring.split('\\n') if len(i) > 3]
  nlines = len(resspl)
  header = resspl[1].split()
  footer = resspl[-2]
  # print(footer)
  content = resspl[2:-2]
  if (len(content) >= 0 ):
    for line in content:
      curJob = jobentry
      contentline = line.split()

      # Remove useless entry
      del(contentline[1]) 

      # Reformat date
      contentline[2] = contentline[2] + ' ' + contentline[3]
      del(contentline[3])

      for i in range(len(header)):
        _key = header[i].lower()
        _entry = contentline[i]
        if _key in k:
          val = _entry
          val = '0' if val=='_' else val
          curJob[_key] = val

      retval.append(curJob)

  if len(retval) > 0:
    totaljobsqueued = sum([int(j['total']) for j in retval])
    totaljobsdone = sum([int(j['done']) for j in retval])
    has_running_update[username] = True
  else:
    totaljobsqueued = 0
    totaljobsdone = 0
    has_running_update[username] = False
  totalstats = {
    "total": totaljobsqueued,
    "done": totaljobsdone,
    "removed": re.sub(".* ([0-9]*) removed,.*", '\\1', footer),
    "run": re.sub(".* ([0-9]*) running,.*", '\\1', footer),
    "idle": re.sub(".* ([0-9]*) idle,.*", '\\1', footer),
    "hold": re.sub(".* ([0-9]*) held,.*", '\\1', footer),
  }

  if not has_high_held_jobs[username] and int(totalstats['hold']) > HOLD_ALERT_RANGE:
    has_high_held_jobs[username] = True
    print('- Noticed high held jobs for ' + username)

  if has_high_held_jobs[username] and int(totalstats['hold']) == 0:
    has_high_held_jobs[username] = False
    has_alerted_held[username] = False
    print('- Reset high held jobs for ' + username)


  return(retval, totalstats)


# execution block
if __name__ == '__main__':
  #print("Opening SSH connection...")
  #sshconnection = open_ssh_connection()

  print("Establishing connection to Discord...")
  intents = discord.Intents.default()
  intents.messages = True
  intents.members = True
  intents.guilds = True

  client = discord.Client(intents=intents)

  @client.event
  async def on_ready():
      global ssh_task
      global status_task
      print(f'Success! Logged in as {client.user}')
      print("Status Log:")
      ssh_task = client.loop.create_task(refresh_ssh())
      await asyncio.sleep(2) # give it some time to establish initial ssh connection
      if STATUS_CHANNEL_ID is not None and MOBILE_CHANNEL_ID is not None:
        status_task = client.loop.create_task(refresh_status())

  @client.event
  async def on_error(event, *args, **kwargs):
    global ssh_task
    global status_task
    message=args[0]
    print('- ERROR:' + args)
    print('- Restarting jobs...')
    ssh_task.cancel()
    ssh_task = client.loop.create_task(refresh_ssh())
    print('- SSH task restarted!')
    await asyncio.sleep(2)
    status_task.cancel()
    status_task = client.loop.create_task(refresh_status())

  @client.event
  async def refresh_status():
    global sshconnection
    global update_ctr
    global has_high_held_jobs
    global has_alerted_held
    global first_update
    while True:
      statuslog = []
      # Update status channel message
      if STATUS_CHANNEL_ID is not None:
        schannel = client.get_channel(STATUS_CHANNEL_ID)
        smsgid = schannel.last_message_id
        outmsg = MSG_all_user_summaries(sshconnection, USERNAMES)
        if smsgid is None:
          await schannel.send(outmsg)
          statuslog.append('- Sent new status message')
        else:
          smsg = await schannel.fetch_message(smsgid)
          await smsg.edit(content=outmsg)
          statuslog.append('- Edited status message ' + str(smsgid))

      # Update mobile channel message
      if MOBILE_CHANNEL_ID is not None:
        mchannel = client.get_channel(MOBILE_CHANNEL_ID)
        mmsgid = mchannel.last_message_id
        outmsg = MSG_all_mobile_summaries(sshconnection, USERNAMES)
        if mmsgid is None:
          await mchannel.send(outmsg)
          statuslog.append('- Sent new mobile message')
        else:
          mmsg = await mchannel.fetch_message(mmsgid)
          await mmsg.edit(content=outmsg)
          statuslog.append('- Edited mobile message ' + str(mmsgid))

      # Check if job status has changed
      if RESPONSE_CHANNEL_ID is not None:
        rchannel = client.get_channel(RESPONSE_CHANNEL_ID)
        # Send notification if job status has changed
        global has_running_update
        global has_running_jobs

        # local just in case something changes, want to be careful with asyncs
        local_hru = has_running_update
        local_hrj = has_running_jobs
        for user in USERNAMES:
          if local_hrj[user] != local_hru[user]:
            if len(notif_list[user]) != 0:
              notifystring = ' '.join([u.mention for u in notif_list[user]])
            else:
              notifystring = ''
            if (has_running_update):
              outmsg = '`' + user + "` launched new jobs!\n" + notifystring
            else:
              outmsg = '`' + user + "`'s jobs have finished!\n" + notifystring
            if not first_update:
              await rchannel.send(outmsg)
              statuslog.append('- User ' + user + ' had a change in job status')
        has_running_update = has_running_jobs
      
        # Check for high held jobs
        for user in USERNAMES:
          if has_high_held_jobs[user] and not has_alerted_held[user]:
            if len(notif_list[user]) != 0:
              notifystring = ' '.join([u.mention for u in notif_list[user]])
            else:
              notifystring = ''
            outmsg = 'ALERT: `' + user + "` has high held jobs.\n" + notifystring
            if not first_update:
              await rchannel.send(outmsg)
            has_alerted_held[user] = True
            statuslog.append('- User ' + user + ' had high held jobs')

      first_update = False
      if update_ctr == 0:
        print("\n".join(statuslog))
      update_ctr = (update_ctr + 1) % 1
      await asyncio.sleep(STATUS_REFRESH_TIME)

  @client.event
  async def refresh_ssh():
    global sshconnection
    while True:
      if sshconnection is not None:
        sshconnection.close()
        sshconnection = None
      sshconnection = open_ssh_connection()
      await asyncio.sleep(SSH_REFRESH_TIME*60)

  @client.event
  async def on_custom_event():
    global sshconnection
    global status_message

    # Refresh SSH connection
    if sshconnection is not None:
      sshconnection.close()
      sshconnection = None
    sshconnection = open_ssh_connection()
    print('- Updated SSH connection [FORCED]')
    
    # Update status channel
    if STATUS_CHANNEL_ID is not None:
      schannel = client.get_channel(STATUS_CHANNEL_ID)
      smsgid = schannel.last_message_id
      outmsg = MSG_all_user_summaries(sshconnection, USERNAMES)
      if smsgid is None:
        await schannel.send(outmsg)
        print('- Sent new status message [FORCED]')
      else:
        smsg = await schannel.fetch_message(smsgid)
        await smsg.edit(content=outmsg)
        print('- Edited status message ' + str(smsgid) + ' [FORCED')

    # Update mobile channel message
    if MOBILE_CHANNEL_ID is not None:
      mchannel = client.get_channel(MOBILE_CHANNEL_ID)
      mmsgid = mchannel.last_message_id
      outmsg = MSG_all_mobile_summaries(sshconnection, USERNAMES)
      if mmsgid is None:
        await mchannel.send(outmsg)
        print('- Sent new mobile message [FORCED]')
      else:
        mmsg = await mchannel.fetch_message(mmsgid)
        await mmsg.edit(content=outmsg)
        print('- Edited mobile message ' + str(mmsgid) + '[FORCED]')

  @client.event
  async def on_message(message):
      if message.author == client.user:
        return
      if not message.content.startswith('!'):
        return

      ipt = message.content[1:]
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
          global notif_list

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


