import discord
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

THUMBS_UP_EMOJI = '\N{THUMBS UP SIGN}'

lastupdate = [datetime.now() for i in range(len(USERNAMES))]
lastseen = [0 for i in range(len(USERNAMES))]
ssh_reconnect = datetime.now()
sshconnection = None
status_message = None


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
  print("Connecting to host " + OSGNODE + " with username '" + OSGUSERNAME + "'...")
  client.connect(hostname=OSGNODE, username=OSGUSERNAME, pkey=k)
  print("Connected!")

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

  totalstats = {
    "total": re.sub(".*query: ([0-9]*) jobs;.*", '\\1', footer),
    "done": re.sub(".* ([0-9]*) completed,.*", '\\1', footer),
    "removed": re.sub(".* ([0-9]*) removed,.*", '\\1', footer),
    "run": re.sub(".* ([0-9]*) running,.*", '\\1', footer),
    "idle": re.sub(".* ([0-9]*) idle,.*", '\\1', footer),
    "hold": re.sub(".* ([0-9]*) held,.*", '\\1', footer),
  }


  return(retval, totalstats)



if __name__ == '!__main__':
  print("Opening SSH connection...")
  sshconnection = open_ssh_connection()
  #gend_msg = get_all_jobs_status(sshconnection)
  print(MSG_all_user_summaries(sshconnection, USERNAMES))
  print(MSG_most_recent_job(sshconnection, 'ahl'))
  print(MSG_all_user_jobs(sshconnection, 'ahl'))
  print(MSG_all_user_summaries(sshconnection, ['ahl']))

if __name__ == '__main__':
  #print("Opening SSH connection...")
  #sshconnection = open_ssh_connection()

  print("Establishing connection to Discord...")
  intents = discord.Intents.default()
  intents.messages = True

  client = discord.Client(intents=intents)

  @client.event
  async def on_ready():
      print(f'Success! Logged in as {client.user}')
      client.loop.create_task(refresh_ssh())
      await asyncio.sleep(5) # give it some time to establish initial ssh connection
      client.loop.create_task(refresh_status())

  @client.event
  async def refresh_status():
    global sshconnection
    global status_message
    while True:
      outmsg = MSG_all_user_summaries(sshconnection, USERNAMES)
      if status_message is None:
        statuschannel = client.get_channel(STATUS_CHANNEL_ID)
        status_message = await statuschannel.send(outmsg)
      else:
        await status_message.edit(content=outmsg)
      await asyncio.sleep(STATUS_REFRESH_TIME)

  @client.event
  async def refresh_ssh():
    global sshconnection
    global status_message
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
    if sshconnection is not None:
      sshconnection.close()
      sshconnection = None
    sshconnection = open_ssh_connection()
    outmsg = MSG_all_user_summaries(sshconnection, USERNAMES)
    if status_message is None:
      statuschannel = client.get_channel(STATUS_CHANNEL_ID)
      status_message = await statuschannel.send(outmsg)
    else:
      await status_message.edit(content=outmsg)

  @client.event
  async def on_message(message):
      if message.author == client.user:
        return
      if not message.content.startswith('!'):
        return

      ipt = message.content[1:]
      if ipt == 'all':
        outmsg = MSG_all_user_summaries(sshconnection, USERNAMES)
      elif ipt == 'h' or ipt == 'help':
        outmsg = MSG_help_str()
      elif ipt == 'update':
        await message.add_reaction(THUMBS_UP_EMOJI)
        client.dispatch("custom_event")
        return
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
      await message.channel.send(outmsg) 


  client.run(DISCORD_TOKEN)


