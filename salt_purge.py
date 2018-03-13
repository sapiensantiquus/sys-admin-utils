#!/bin/env python

import logging, threading, signal, thread
from subprocess import Popen,PIPE,STDOUT,call
from time import sleep
from sys import argv

# Limit to 10 threads so we aren't purging too many concurrent keys
threadLimiter = threading.BoundedSemaphore(int(argv[1]))
# List of hosts that failed to reauthenticate!
failed = []


# If we ctrl + c, let's make sure to propagate to master process with exception
class ExitCommand(Exception):
    pass

# Signal handler for ctrl + c, uses above exception
def signal_handler(signal, frame):
    raise ExitCommand()

# Function for purging keys. Used in the context of a thread.
def run(line):
  try:
    logging.info("Attempting to test.ping {}".format(line))
    salt_ping=Popen("/usr/bin/salt {} test.ping".format(line), shell=True, stdout=PIPE, stderr=PIPE)
    output=salt_ping.communicate()

    if 'No response' in output[0] or 'No return' in output[1]:
      logging.warning("{} is currently inaccessible...".format(line))

    else:
      logging.info("{} is accessible. Skipping...".format(line))
      return
  
    logging.info("Purging key: {}".format(line))
    salt_key_purge=Popen("/usr/bin/salt-key -d {}".format(line), shell=True, stdout=PIPE, )

    # Give time to reauthenticate
    sleep(60)

    # Technically we may have not given these hosts enough time. Make sure to 
    # drop failed auth hosts into a file for post-processing.
    salt_ping_after=Popen("/usr/bin/salt {} test.ping".format(line), shell=True, stdout=PIPE, stderr=PIPE)
    output_after=salt_ping_after.communicate()
    if 'No response' in output_after[0] or 'No return' in output_after[1]:
      logging.error("{} is still inaccessible...".format(line))
      failed.append(line)
    else:
      logging.info("{} was succesfully re-added!".format(line)) 
    
  finally:
    threadLimiter.release()

# Copy inaccessible hosts into this
down_hosts = []
try:
  with open(argv[2]) as down:
    down_hosts_raw = down.readlines()
    down_hosts = [line[2:] for line  in down_hosts_raw]
    for l in down_hosts:
      line = l[:-1]
      threadLimiter.acquire()
      signal.signal(signal.SIGINT, signal_handler)
      thread = threading.Thread(target=run,args=(line,))
      thread.setDaemon(True)
      thread.start()
except ExitCommand:
  pass
finally:
  with open('failed.txt', 'w') as failed_hosts:
    for host in failed:
      failed_hosts.write("- {}\n".format(host))
  logging.warning("The following hosts failed to reauthenticate! {}".format(failed,))


