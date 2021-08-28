import logging
import sys

from ConfigObject import ConfigObject

logger = logging.getLogger('configLoader')
config = ConfigObject(filename = 'config.ini')

try: ##Check if config.ini exist, if not, create a new file and kill the program
  f = open('config.ini')
  f.close()
except IOError as e:
  logger.critical('config.ini not found, generating one now. Please fill it in.')
  config['settings']['token'] = ''
  config['settings']['ownerID'] = '180067685986467840'
  config['database']['db_name'] = ''
  config['database']['db_user'] = ''
  config['database']['db_password'] = ''
  config['database']['db_host'] = ''
  config['database']['db_port'] = ''
  config.write()
  sys.exit()

class settings:
  token = config['settings']['token']
  owner = config['settings']['ownerID'].as_int()
  db_name = config['database']['db_name']
  db_user = config['database']['db_user']
  db_password = config['database']['db_password']
  db_host = config['database']['db_host']
  db_port = config['database']['db_port'].as_int()