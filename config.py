"""
Obtain configuration values from 
the environment or a configuration file. 

Known configuration values are:
   app_key  (a string used to cryptographically sign cookies)

Approach:  Environment takes precedence.  We read
  configuration file only if present in "app.conf"

"""
import os
import logging
import configparser

# Configuration files, in order of access.  Later in order
# overrides earlier, so start with public defaults and then
# visit per-installation and/or per-user secrets for passwords,
# tokens, etc. 
CONFIG_FILES = [ "config_public.ini", "config_private.ini"]

logging.basicConfig(level=logging.DEBUG)

config_keys = [ "app_key", "debug", "port", "host" ]
config_dict = { }

translations = { "true": True, "false": False }

config = configparser.ConfigParser()
have_file = False
for config_file_path in CONFIG_FILES: 
    if os.path.exists(config_file_path):
        logging.info(f"Loading configuration file {config_file_path}")
        have_file = True
        config.read(config_file_path)
if have_file: 
    for group in config:
        for key in config[group]:
            logging.debug(f"Config[{group}][{key}] = {config[group][key]}") 

# The only API function
#
def get(key):
    logging.debug(f"Looking up configuration key '{key}'")
    if key in os.environ:
        val = os.environ[key]
        logging.debug(f"Found config value '{val}' in environment")
    elif have_file:
        logging.debug(f"No key '{key}' in os.environ")
        val= config['DEFAULT'][key]
        logging.debug(f"Found config value '{val}' in config file")
    else:
        raise NameError("Config option not defined: {}".format(key))
    
    if val in translations:
        val = translations[val]
    return val








    


