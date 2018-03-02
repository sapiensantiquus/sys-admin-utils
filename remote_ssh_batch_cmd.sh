#!/bin/bash
set -e
# Runs a command with sudo on a list of remote hosts using password-based auth
# Dependencies: sshpass
# Arguments:
# 1. Hosts file containing all host names on which the command will be run
# 2. User name of user attempting to run SSH command
# 3. Command to run (be sure to put in quotes!)
read -p "Password: " -s password
while read HOST  ; do
        sshpass -f <(printf '%s\n'  $password) ssh -t "$2"@"$HOST" << EOF
                sleep 15
                echo "$password" | sudo -S $3
EOF
done <$1

