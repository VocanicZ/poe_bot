#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import sys
import time
from ast import literal_eval

from utils.gamehelper import Poe2Bot


# In[ ]:





# In[3]:


notebook_dev = False
# readability
poe_bot_class = Poe2Bot
poe_bot: poe_bot_class


# In[ ]:


default_config = {
  "REMOTE_IP": "192.168.47.51",  # z2
  "unique_id": "poe_2_test",
  "force_reset_temp": False,
}


try:
  i = sys.argv[1]
  print(i)
  parsed_config = literal_eval(i)
  print("successfully parsed cli config")
  print(f"parsed_config: {parsed_config}")
except:
  print("cannot parse config from cli, using default\dev one")
  notebook_dev = True
  parsed_config = default_config

config = {}

for key in default_config.keys():
  config[key] = parsed_config.get(key, default_config[key])

print(f"config to run {config}")


# In[ ]:


REMOTE_IP = config["REMOTE_IP"]  # REMOTE_IP
UNIQUE_ID = config["unique_id"]  # unique id
force_reset_temp = config["force_reset_temp"]
print(f"running test using: REMOTE_IP: {REMOTE_IP} unique_id: {UNIQUE_ID}  force_reset_temp: {force_reset_temp}")


# In[ ]:


poe_bot = Poe2Bot(unique_id=UNIQUE_ID, remote_ip=REMOTE_IP)
poe_bot.refreshAll()
poe_bot.game_data.terrain.getCurrentlyPassableArea()
# TODO move it to poe_bot.refreshAll() refreshed_data["c_t"] ## "c_t":0 - mouse || "c_t":1 - wasd
poe_bot.mover.setMoveType("wasd")