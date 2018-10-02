# app expects all IZs to be on the same instance for now
ALMA_API = 'https://api-na.hosted.exlibrisgroup.com/almaws/'

# name each alma IZ and add the api key
ALMA_INSTANCES = {
    'my_iz'	: 'apikey',
    'your_iz'	: 'apikey',
}

# this maps the library names to the izs that they belong to
INST_MAP = {
    'my_main_library'		: 'my_iz',
    'my_other_library'		: 'my_iz',
    'your_other_library'	: 'your_iz',
    'your_other_library'	: 'your_iz',
}
