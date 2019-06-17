# WRLC Fines app
Status: minimally viable product (MVP) release

This application allows circulation staff to accept fine payments for fines assessed by other Alma institution zones. It marks the fines payed in the lending IZ, and keeps an audit log of transactions.

## Installation
Clone this repository.
```
git clone git@github.com:WRLC/alma-fines.git
```
You can clone over https: `https://github.com/WRLC/alma-fines.git`

Set up python
```
virtualenv -p python3.6 ENV
source ENV/bin/activate
pip install -r requirements.txt
cp settings.template.py settings.py
```
Configure the settings.py file to match your environemnt.

Run this app
```
gunicorn -b 127.0.0.1:8000 wsgi:app
```
On WRLC servers we run this app in a Green Unicorn (Python WSGI HTTP Server) service. 
```
systemctl enable alma-fines.services
```
The daemon is started and stoped via systemd. The config is `/etc/systemd/system/alma-fines.service`

## Tests
After configuring settings.py, run `pytest-3 -v` (or equivalent in your python environment) to be sure you've configured settings.py with valid API keys. Further unit tests are needed (see issue #18 ).

## Staff Authentication
This application assumes another system for authentication and authorization that will communicate with this one via a [JSON Web Token](https://jwt.io/). The JWT is passed in a cookie name `wrt`. The shared secret used to decode the token is defined in `settings.py`. The token is expected to include four data elements:

| Key | Description |
| -------------- | --------------------------- |
| ['primary_id'] | the staff user's id in Alma |
| ['inst'] | the staff user's institution code as specified in the `ALMA_INSTANCES` settings |
| ['full_name'] | the staff user's display name |
| ['authorizations'] | a list of the permissions granted this staff user by the authN/authZ system based on roles in Alma; it must include an authorization named `fines_payment` in order to access this application |

WRLC's authN/authZ system uses SAML to authenticate users from their home institutions' Identity Providers and the Alma user API to look them up in Alma and check Circulation roles for authorization. 
The institutions are currently hard-coded in `templates/login.html` and the URL to send the user to login is hard-coded in `static/js/frontend.js`.
To integrate with your service provider login you will need to change those files (at least until we properly extract those variables to `settings.py`--see issue #29 ).
A simpler authN/authZ system that maintains its own list of users could also work.

### Important!
For testing for various IZs where we don't have staff accounts we created a "backdoor" that let's you login with a URL like https://fines.example.edu/backdoor/IZ. You MUST protect this URL from general usage (we use Nginx IP access control along with HTTP basic authentication) or turn it off in `fines_app.py`.
