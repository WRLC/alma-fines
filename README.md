# WRLC Fines app
UNDER DEVELOPMENT

This application allows circulation workers to accept fine payments for fines assessed by other Alma institution zones. It marks the fines payed in the lending IZ, and keeps an audit log of transactions. The audit log can be used to do a monthly fine payment reconciliation between libraries.

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
```
Run this app
```
gunicorn -b 127.0.0.1:8000 wsgi:app
```
### testing
test
