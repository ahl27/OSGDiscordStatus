#!/bin/sh

# install discord api
echo "Installing python discord API..."
python3 -m pip install -U discord.py
python3 -m pip install paramiko
python3 -m pip install asyncio

echo "\nDone!\n"
echo "YOU WILL NEED AN API KEY TO RUN THIS SCRIPT"
echo "GO TO https://discord.com/developers/applications TO CREATE ONE"
echo "\nBe sure to fill in your details in CREDENTIALS.py!"
touch CREDENTIALS.py
echo \# SSH Key will typically be in /Users/USERNAME/.ssh/id_rsa > CREDENTIALS.py
echo PATH_TO_SSH_KEY=\"complete/path/to/ssh/key\" >> CREDENTIALS.py
echo SSHKEY_PWD=None >> CREDENTIALS.py
echo \\n\# This can be found or created at https://discord.com/developers/applications >> CREDENTIALS.py
echo DISCORD_BOT_TOKEN=\"YOUR KEY HERE\" >> CREDENTIALS.py 
echo \\n\# OSG Login Info >> CREDENTIALS.py
echo OSGLOGIN=\"USERNAME\" >> CREDENTIALS.py
echo OSGNODE=\"loginXX.osgconnect.net\" >> CREDENTIALS.py
echo \\n\# Comma-separated list of all usernames to check >> CREDENTIALS.py
echo USERS_TO_CHECK=[\"EXAMPLEUSER1\", \"EXAMPLEUSER2\"] >> CREDENTIALS.py
echo "\\n# Length of time (in seconds) between status refresh cycles" >> CREDENTIALS.py
echo STATUS_REFRESH_TIME=30 >> CREDENTIALS.py
echo "# Length of time (in minutes) between ssh refresh cycles" >> CREDENTIALS.py
echo SSH_REFRESH_TIME=5 >> CREDENTIALS.py

echo \\n\# REGULARLY UPDATED CHANNELS >> CREDENTIALS.py
echo \# Set to None to disable this functionality >> CREDENTIALS.py
echo \# ex:  >> CREDENTIALS.py
echo \#\\t STATUS_CHANNEL_ID=None >> CREDENTIALS.py
echo \#\\t STATUS_CHANNEL_ID=000000000000000000 >> CREDENTIALS.py
echo \# 18 digit ID of status channel, can be found on Discord >> CREDENTIALS.py
echo STATUS_CHANNEL_ID=None >> CREDENTIALS.py
echo \# 18 digit ID of mobile-formatted status channel, can be found on Discord >> CREDENTIALS.py
echo STATUS_CHANNEL_ID=None >> CREDENTIALS.py
