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

config_file_path = "app.conf"

logging.basicConfig(level=logging.DEBUG)

config_keys = [ "app_key", "debug", "port", "host" ]
config_dict = { }

translations = { "true": True, "false": False }

have_file = False
if os.path.exists(config_file_path):
    logging.info("Loading configuration file")
    have_file = True
    config = configparser.ConfigParser()
    config.read(config_file_path)
    for group in config:
        for key in config[group]:
            logging.debug(f"Config[{group}][{key}] = {config[group][key]}") 

else:
    logging.info("No configuration file present")

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








    


