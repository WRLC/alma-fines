# app expects all IZs to be on the same instance for now
ALMA_API = 'https://api-na.hosted.exlibrisgroup.com/almaws/'

# name each alma IZ and add the api key
ALMA_INSTANCES = {
    'iza' : {
             'key'      : 'apikey',
             'name'     : 'Your IZ Name',
             'code'     : 'IZID',
            },
    'izb'  : { 'key'  : 'apikey',
             'name' : 'Your IZ Name',
             'code' : 'IZID',
}

# this maps the library names to the izs that they belong to
INST_MAP = {
    'my_main_library'		: 'my_iz',
    'my_other_library'		: 'my_iz',
    'your_other_library'	: 'your_iz',
    'your_other_library'	: 'your_iz',
}

# transaction log file
LOG_FILE = './audit.log'

# Secret key for session signing. Fill in with some random bytes
SESSION_KEY = 'somerandomebytes'
