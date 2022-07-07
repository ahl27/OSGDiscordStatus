import discord
import subprocess
import paramiko
import re
from datetime import datetime
import CREDENTIALS

DISCORD_TOKEN = CREDENTIALS.DISCORD_BOT_TOKEN
OSGUSERNAME = CREDENTIALS.OSGLOGIN
OSGNODE = CREDENTIALS.OSGNODE
USERNAMES = CREDENTIALS.USERS_TO_CHECK
lastupdate = [datetime.now() for i in range(len(USERNAMES))]
lastseen = [0 for i in range(len(USERNAMES))]
ssh_reconnect = datetime.now()


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
  k = paramiko.RSAKey.from_private_key_file(CREDENTIALS.PATH_TO_SSH_KEY)
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  print("Connecting to host " + OSGNODE + " with username '" + OSGUSERNAME + "'...")
  client.connect(hostname=OSGNODE, username=OSGUSERNAME, pkey=k)
  print("Connected!")

  return(client)

# Get status summary for all users
def get_all_jobs_status(client):
  if client is None:
    return("Error: SSH Client not established.")
  totalmsg = ''
  for username in USERNAMES:
    msg = get_job_status_string(client, username)
    totalmsg = totalmsg + msg
  return(totalmsg)

# Gets status summary of all jobs for a given user
def get_job_status_string(client, username):
  if client is None:
    return("Error: SSH Client not established.")
  totalmsg = ''
  jobs, total = get_jobs_for_user(client, username)
  msg = username + "\n```\n" + \
          "Jobs: " + total['total'] + '\n' + \
          "Completed: " + total['done'] + '\n' + \
          "Removed: " + total['removed'] + '\n' + \
          "Running: " + total['run'] + '\n' + \
          "Idle: " + total['idle'] + '\n' + \
          "Held: " + total['hold'] + '\n' + \
          "```\n\n"
  return(msg)

# Converts dict of job to status string
def jobentry_to_string(jobentry):
  jobstr = "Batch " + jobentry['batch_name'] + ":\t" + \
            str(jobentry['done']) + " done,\t" + \
            str(jobentry['run']) + " running,\t" + \
            str(jobentry['idle']) + " idle,\t" + \
            str(jobentry['hold']) + " held,\t" + \
            str(jobentry['total']) + " total.\n"
  return(jobstr)

# Gets all individual job status output for a particular user
def get_indiv_jobs(client, username):
  if client is None:
    return("Error: SSH Client not established.")
  jobs, total = get_jobs_for_user(client, username)
  outmsg = "Jobs for user `" + username + "`\n```\n"
  if (len(jobs) == 0):
    outmsg += 'No jobs found.'
  else:
    for job in jobs:
      outmsg += jobentry_to_string(job)
  outmsg += '```\n'
  return(outmsg)

# Get most string for most recent job for given user 
def get_most_recent_job(client, username):
  if client is None:
    return("Error: SSH Client not established.")
  jobs, total = get_jobs_for_user(client, username)
  outmsg = "Most recent job for user `" + username + "`\n```\n"
  if (len(jobs) == 0):
    outmsg += 'No jobs found.'
  jobtimes = [datestring_to_datetime(job['submitted']) for job in jobs]
  most_recent = jobtimes.index(min(jobtimes))
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



if __name__ == '!!!__main__':
  print("Opening SSH connection...")
  sshconnection = open_ssh_connection()
  #gend_msg = get_all_jobs_status(sshconnection)
  print(get_indiv_jobs(sshconnection, 'ahl'))

if __name__ == '__main__':
  print("Opening SSH connection...")
  sshconnection = open_ssh_connection()

  print("Establishing connection to Discord...")
  intents = discord.Intents.default()
  intents.messages = True

  client = discord.Client(intents=intents)

  @client.event
  async def on_ready():
      print(f'Success! Logged in as {client.user}')

  @client.event
  async def on_message(message):
      if message.author == client.user:
          return
      if message.content.startswith('!'):
        ipt = message.content[1:]
        if ipt == 'all':
          outmsg = get_all_jobs_status(sshconnection)
        else:
          mostrecent = False
          alljobs = False
          if ipt.startswith('!'):
            mostrecent = True
            ipt = ipt[1:]
          elif ipt.startswith('job'):
            alljobs = True
            ipt = ipt.split()[1]
          if ipt in USERNAMES:
            if mostrecent:
              outmsg = get_most_recent_job(sshconnection, ipt)
            elif alljobs:
              outmsg = get_indiv_jobs(sshconnection, ipt)
            else:
              outmsg = get_job_status_string(sshconnection, ipt)
          else:
            outmsg = "Error: username `" + ipt + "` is not allowed to be queried."
        await message.channel.send(outmsg) 


  client.run(DISCORD_TOKEN)


