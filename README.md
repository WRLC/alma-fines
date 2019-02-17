# WRLC Fines app
Status: minimally viable product (MVP) release

This application allows circulation workers to accept fine payments for fines assessed by other Alma institution zones. It marks the fines payed in the lending IZ, and keeps an audit log of transactions.

## Installation
Clone this repository. Non WRLC people can clone over https: https://github.com/WRLC/alma-fines.git
```
git clone git@github.com:WRLC/alma-fines.git
```
Set up python
```
virtualenv -p python3.6 ENV
source ENV/bin/activate
pip install -r requirements.txt
cp settings.template.py settings.py
```
Configure the settings.py file to match your environemnt.

On WRLC servers this app runs in a Green Unicorn (Python WSGI HTTP Server) service. 
```
systemctl enable alma-fines.services
```
The daemon is started and stoped via systemd. The config is `/etc/systemd/system/alma-fines.service`

### Tests
After configuring settings.py, run `pytest -v` to be sure you've configured settings.py with valide API keys.
Run this app
```
gunicorn -b 127.0.0.1:8000 wsgi:app
```
