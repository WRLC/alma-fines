from flask import Flask, abort, redirect, render_template, request, session, url_for, current_app
from pymemcache.client.base import Client as memcacheClient
from functools import wraps
import json
import jwt
import logging
from logging.handlers import TimedRotatingFileHandler
import requests
import settings

app = Flask(__name__)

# set up logging to work with WSGI server
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

app.config['ALMA_API'] = settings.ALMA_API
app.config['ALMA_INSTANCES'] = settings.ALMA_INSTANCES
app.config['ALMA_INSTANCES'] = settings.ALMA_INSTANCES
app.config['INST_MAP'] = settings.INST_MAP
app.config['SESSION_KEY']= settings.SESSION_KEY
app.config['TEST_USERS'] = settings.TEST_USERS
app.config['FEE_RESOURCE'] = 'almaws/v1/users/{}/fees/{}'
app.config['FEES_RESOURCE'] = 'almaws/v1/users/{}/fees'
app.config['USER_RESOURCE'] = 'almaws/v1/users/{}'
app.config['USERS_RESOURCE'] = 'almaws/v1/users'
app.config['SHARED_SECRET'] = settings.SHARED_SECRET
app.config['LOG_FILE'] = settings.LOG_FILE
app.config['COMMENT_TAG'] = settings.COMMENT_TAG
app.config['COOKIE_NAME'] = settings.COOKIE_NAME
app.config['MEMCACHED_SERVER'] = settings.MEMCACHED_SERVER

app.secret_key = app.config['SESSION_KEY']

# set up error handlers & templates for HTTP codes used in abort()
#   see http://flask.pocoo.org/docs/1.0/patterns/errorpages/
@app.errorhandler(400)
def badrequest(e):
    return render_template('error_400.html'), 400
@app.errorhandler(403)
def forbidden(e):
    return render_template('unauthorized.html'), 403
@app.errorhandler(500)
def internalerror(e):
    return render_template('error_500.html'), 500

# audit log
audit_log = logging.getLogger('audit')
audit_log.setLevel(logging.INFO)
file_handler = TimedRotatingFileHandler(app.config['LOG_FILE'], when='midnight')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s\t%(message)s'))
audit_log.addHandler(file_handler)

# decorator for pages that need auth
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not 'username' in session:
            return redirect(url_for('login'))
        else:
            return f(*args, **kwargs)
            
    return decorated

@app.route('/')
@auth_required
def index():
    return render_template('index.html',
                           institutions=app.config['ALMA_INSTANCES'].keys())

@app.route('/login')
def login():
    if 'username' in session:
        return redirect(url_for('index'))
    else:
        url = settings.SAML_SP + settings.COOKIE_ISSUING_FILE + '?service=' + settings.SERVICE_SLUG
        return redirect(url)

@app.route('/login/n', methods=['GET'])
def new_login():
    session.clear()
    if 'AladinSessionFines' in request.cookies:
        memcached_key = request.cookies[current_app.config['COOKIE_NAME']]  # get the login cookie
        memcached = memcacheClient((current_app.config['MEMCACHED_SERVER'], 11211))
        user_data = {}
        for line in memcached.get(memcached_key).decode('utf-8').splitlines():
            key, value = line.split('=')
            user_data[key] = value
        session['username'] = user_data['UserName']
        session['user_home'] = settings.IDP_ALMA_MAP[user_data['University']]
        user_data['full_name'] = ''
        if 'GivenName' in user_data:
            user_data['full_name'] += user_data['GivenName'] + ' '
        if 'Name' in user_data:
            user_data['full_name'] += user_data['Name']
        session['display_name'] = user_data['full_name']
        return redirect(url_for('index'))
    else:
        return "no login cookie"

@app.route('/logout')
@auth_required
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/user', methods=['GET', 'POST'])
@auth_required
def show_fines():
    if request.method == 'GET':
        return redirect(url_for('index'))
    else:
        uid = request.form['uid']
        # build fees data
        user_fines = {'all_fees':[],
                      'uid':uid}
        app.logger.debug('Searching for '+session['user_home']+' user '+uid+' fines')
        lenders = []
        for lender in app.config['ALMA_INSTANCES']:
            if lender == session['user_home']:
                # this is the users home institution, get full name
                try:
                    home_account = _get_user(lender, uid)
                    app.logger.debug('_get_user() returned a ' + type(home_account).__name__)
                    if 'full_name' in home_account:
                        patron_name = home_account['full_name']
                    else:
                        app.logger.error('Unexpected response for home_account (full_name missing)')
                        abort(500)
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code
                    if status_code == 400:
                        errors = json.loads(e.response.text)
                        for err in errors['errorList']['error']:
                            app.logger.debug(err['errorCode']+': '+err['errorMessage'])
                            if err['errorCode'] == '401861':
                                return render_template( 'user_not_found.html',
                                                        uid=uid, inst=lender )
                    app.logger.error('GET /almaws/v1/users/'+uid+' returned '+e.response.text)
                    abort(status_code)
                except requests.exceptions.RequestException as e:
                    app.logger.error('POST /user/'+uid+' exception: '+e.response.text)
                    abort(500)
            elif app.config['ALMA_INSTANCES'][lender]['is_lender']:
                lenders.append(lender)

        for lender in lenders:
            try:
                linked_account = _get_linked_user(session['user_home'], 
                                                  lender, 
                                                  uid)
                # if now error was thrown from _get_linked_user
                # an account was found, check for fines
                lending_name = app.config['ALMA_INSTANCES'][lender]['name']
                fines = _get_fines(lender, linked_account['primary_id'])
                if fines['total_record_count'] > 0:
                    iz_fees = {'fees': []} 
                    iz_fees['lender'] = lender 
                    iz_fees['display_name'] = ', '.join([linked_account['last_name'],
                                                         linked_account['first_name']])
                    iz_fees['inst_display_name'] = app.config['ALMA_INSTANCES'][lender]['name']
                    for fee in fines['fee']:
                        iz_fees['fees'].append(fee)
                    user_fines['all_fees'].append(iz_fees)
            except requests.exceptions.HTTPError:
                # no fines at this instiution
                pass

        if len(user_fines['all_fees']) > 0:
            return render_template('user_fines.html',
                                   data=user_fines,
                                   patron_name=patron_name)
        else:
            return render_template('user_no_fines.html',
                                   data=user_fines,
                                   patron_name=patron_name)

@app.route('/payment', methods=['GET','POST'])
@auth_required
def payment():
    payment_queue = json.loads(request.form['payments'])
    patron_name = request.form['patron_name']
    payments = []
    for k in payment_queue:
        for fee in payment_queue[k]:
            payment =  _pay_single_fee(k, session['user_home'], fee['link'], fee['amount'])
            audit_log.info('{staff_id}\t{accepted_at}\t{t_id}\t{amount}\t{owner}'
                .format(staff_id=session['username'],
                        accepted_at=session['user_home'],
                        t_id=payment['id'],
                        amount=payment['transaction'][0]['amount'],
                        owner=payment['owner']['value']))

            # add IZ name to payment info
            iz_owner_name = app.config['ALMA_INSTANCES'][_resolve_inst(k)]['name']
            payment['iz_owner_name'] = iz_owner_name
            payments.append(payment)

    # use for testing w/o creating payment (commend out above too)
    #with open('sample.json') as sample:
    #    payments = json.load(sample)
    #return json.dumps(payments)
    return render_template('payment.html',
                           payments=payments,
                           patron_name=patron_name)

@app.route('/backdoor/<inst>')
def backdoor(inst):
    session.clear()
    session['username'] = 'backdoor'
    session['user_home'] = inst
    session['display_name'] = 'backdoor user'
    return redirect(url_for('index'))


@app.route('/testcookie', methods=['GET', 'POST'])
def test_cookie():
    '''
    https://aladin-tst.wrlc.org/simplesaml/wrlcauth/issue.php?institution=wr&url=http://fines.wrlc.org/testcookie
    '''
    if 'wrt' in request.cookies:
        encoded =  request.cookies['wrt']
        decoded = jwt.decode(encoded, 'example_key', algorithms=['HS256'])
        return json.dumps(decoded)
    else:
        return "no login cookie"

# Local functions
def _alma_get(resource, apikey, params=None, fmt='json'):
    '''
    makes a generic alma api call, pass in a resource
    '''
    params = params or {}
    params['apikey'] = apikey
    params['format'] = fmt
    r = requests.get(resource, params=params) 
    r.raise_for_status()
    if fmt == 'json':
        return r.json()
    else:
        return r.content

def _alma_post(resource, apikey, payload=None, params=None, fmt='json'): 
    '''
    makes a generic put request to alma api. puts xml data.
    '''
    payload = payload or {}
    params = params or {}
    params['format'] = fmt
    headers =  {'Authorization' : 'apikey ' + apikey}
    r = requests.post(resource,
                     headers=headers,
                     params=params,
                     data=payload)
    r.raise_for_status()
    if fmt == 'json':
        return r.json()
    else:
        return r.content

def _count_submitted_fees(fees):
    count = 0
    for k in fees:
        count += 1
    return count

def _resolve_inst(inst):
    return(app.config['INST_MAP'][inst])

def _get_fines(inst, uid):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]['key']
    params = {'status':'ACTIVE'}
    response = _alma_get(app.config['ALMA_API'] +
                         app.config['FEES_RESOURCE'].format(uid),
                         api_key,
                         params=params)
    return response

def _get_user(inst, uid):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]['key']
    params = {'apikey':api_key, 'format':'json'}
    response = _alma_get(app.config['ALMA_API'] +
                         app.config['USER_RESOURCE'].format(uid), 
                         api_key,
                         params)
    return response

def _get_linked_user(inst, fines_inst, uid):
    inst_normal = _resolve_inst(inst)
    fines_inst_normal = _resolve_inst(fines_inst)
    api_key = app.config['ALMA_INSTANCES'][fines_inst_normal]['key']
    inst_code = app.config['ALMA_INSTANCES'][inst_normal]['code']
    params = {
              'source_user_id':uid,
              'source_institution_code':inst_code,
             }
    response = _alma_get(app.config['ALMA_API'] +
                         app.config['USERS_RESOURCE'], 
                         api_key,
                         params)
    if response['total_record_count'] > 1:
        app.logger.error('Unexpected # of records for '+inst_code+'::'+uid
                        +' in '+fines_inst+': '+response['total_record_count'])
        return abort(500)
    else:
        return response['user'][0]

def _pay_single_fee(inst, collecting_inst, link, amount):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]['key']
    params = {
              'op' : 'pay',
              'method' : 'ONLINE',
              'amount' : amount,
              'comment' : '{} {}'.format(app.config['COMMENT_TAG'], collecting_inst)
             }
    response = _alma_post(link, api_key, params=params)
    return response


def get_location_code(inst_code):
    return app.config['INST_MAP'][inst_code]

if __name__ == "__main__":
    app.run(debug=True)
