import requests
import settings

def test_instances_configured():
    assert settings.ALMA_INSTANCES, "No Alma instances configured, make sure settings.py is configured"

def test_api_keys_work_read_mode():
	for k,v in settings.ALMA_INSTANCES.items():
		r = requests.get(settings.ALMA_API + 'almaws/v1/users/operation/test',
			params={'apikey' : v['key']})
		assert r.status_code == 200, "API GET request: {} for inst {} failed".format(r.url,k)

def test_api_keys_work_write_mode():
	for k,v in settings.ALMA_INSTANCES.items():
		r = requests.post(settings.ALMA_API + 'almaws/v1/users/operation/test',
      headers={'Authorization' : 'apikey ' + v['key']})
		assert r.status_code == 200, "API POST request: {} for inst {} failed".format(r.url,k)
