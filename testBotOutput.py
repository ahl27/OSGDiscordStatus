from OSGDiscordBot import *

# testing block
if __name__ == '__main__':
  print("Opening SSH connection...")
  sshconnection = open_ssh_connection()
  print(MSG_all_mobile_summaries(sshconnection, USERNAMES))
  #print(MSG_most_recent_job(sshconnection, 'ahl'))
  #print(MSG_all_user_jobs(sshconnection, 'ahl'))
  #print(MSG_all_user_summaries(sshconnection, ['ahl']))