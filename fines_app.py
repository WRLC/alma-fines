from flask import (Flask, redirect, request, render_template,
    request, session, url_for)
from functools import wraps
import json
import jwt
import logging
from logging.handlers import TimedRotatingFileHandler
import requests
import settings

app = Flask(__name__)

app.config['ALMA_API'] = settings.ALMA_API
app.config['ALMA_INSTANCES'] = settings.ALMA_INSTANCES
app.config['ALMA_INSTANCES_NEW'] = settings.ALMA_INSTANCES_NEW
app.config['INST_MAP'] = settings.INST_MAP
app.config['SESSION_KEY']= settings.SESSION_KEY
app.config['TEST_USERS'] = settings.TEST_USERS
app.config['FEE_RESOURCE'] = 'almaws/v1/users/{}/fees/{}'
app.config['FEES_RESOURCE'] = 'almaws/v1/users/{}/fees'
app.config['USER_RESOURCE'] = 'almaws/v1/users/{}'
app.config['USERS_RESOURCE'] = 'almaws/v1/users'
app.config['SHARED_SECRET'] = settings.SHARED_SECRET
app.config['LOG_FILE'] = settings.LOG_FILE

app.secret_key = app.config['SESSION_KEY']

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
        return render_template('login.html')

@app.route('/login/n', methods=['GET'])
def new_login():
    session.clear()
    if 'wrt' in request.cookies:
        encoded_token =  request.cookies['wrt']
        user_data = jwt.decode(encoded_token, app.config['SHARED_SECRET'], algorithms=['HS256'])
        if user_data['primary_id']:
            session['username'] = user_data['primary_id']
            session['user_home'] = user_data['inst']
            session['display_name'] = user_data['full_name']
            return redirect(url_for('index'))
        else:
            return "no username set"
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
        for lender in app.config['ALMA_INSTANCES_NEW']:
            linked_account = _get_linked_user(session['user_home'], 
                                              lender, 
                                              uid)
            if linked_account == 400:
                # linked account not found at lender
                pass
            else:
                # an account was found, check for fines
                lending_name = app.config['ALMA_INSTANCES_NEW'][lender]['name']
                fines = _get_fines(lender, linked_account['primary_id'])
                if fines['total_record_count'] > 0:
                    iz_fees = {'fees': []} 
                    iz_fees['lender'] = lender 
                    iz_fees['display_name'] = ', '.join([linked_account['last_name'],
                                                         linked_account['first_name']])
                    iz_fees['inst_display_name'] = app.config['ALMA_INSTANCES_NEW'][lender]['name']
                    for fee in fines['fee']:
                        iz_fees['fees'].append(fee)
                    user_fines['all_fees'].append(iz_fees)
                else:
                    # no fines were found at this inst
                    pass

        if len(user_fines['all_fees']) > 0:
            return render_template('user_fines.html',
                                   data=user_fines)
        else:
            return render_template('user_no_fines.html',
                                   data=user_fines)

@app.route('/payment', methods=['GET','POST'])
@auth_required
def payment():
    payment_queue = json.loads(request.form['payments'])
    payments = []
    for k in payment_queue:
        for fee in payment_queue[k]:
           payment =  _pay_single_fee(k, fee['link'], fee['amount'])
           audit_log.info(
            '{staff_id}\t{accepted_at}\t{t_id}\t{amount}\t{owner}'.format(staff_id=session['username'],
                                                                          accepted_at=session['user_home'],
                                                                          t_id=payment['id'],
                                                                          amount=payment['transaction'][0]['amount'],
                                                                          owner=payment['owner']['value']))
           payments.append(payment)

    # use for testing w/o creating payment (commend out above too)
    #with open('sample.json') as sample:
    #    payments = json.load(sample)
    #return json.dumps(payments)
    return render_template('payment.html',
                           payments=payments)

@app.route('/backdoor/<inst>')
def backdoor(inst):
    session.clear()
    session['username'] = 'backdoor'
    session['user_home'] = inst
    session['display_name'] = 'backdoor user'
    return redirect(url_for('index'))


@app.route('/testcookie', methods=['GET', 'POST'])
def test_cookie():
    if 'wrt' in request.cookies:
        encoded =  request.cookies['wrt']
        decoded = jwt.decode(encoded, 'example_key', algorithms=['HS256'])
        return json.dumps(decoded)
    else:
        return "no login cookie"

# Local functions

def _count_submitted_fees(fees):
    count = 0
    for k in fees:
        count += 1
    return count

def _resolve_inst(inst):
    return(app.config['INST_MAP'][inst])

def _get_fines(inst, uid):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]
    r = requests.get(app.config['ALMA_API'] +
                     app.config['FEES_RESOURCE'].format(uid) + 
                     '?apikey={}&status=ACTIVE&format=json'.format(api_key))
    if r.status_code != 200:
        return r.raise_for_status()
    else:
        return r.json()

def _get_single_fine(inst, uid, fee_id):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]
    r = requests.get(app.config['ALMA_API'] +
                     app.config['FEE_RESOURCE'].format(uid, fee_id) +
                     '?apikey={}&format=json'.format(api_key))
    return r.json()

def _get_user(inst, uid):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]
    params = {'apikey':api_key, 'format':'json'}
    r = requests.get(app.config['ALMA_API'] +
                     app.config['USER_RESOURCE'].format(uid), 
                     params=params)
    if r.status_code == 400:
        return r.status_code
    elif r.raise_for_status():
        return r.raise_for_status()
    else:
        return r.json()

def _get_linked_user(inst, fines_inst, uid):
    inst_normal = _resolve_inst(inst)
    fines_inst_normal = _resolve_inst(fines_inst)
    api_key = app.config['ALMA_INSTANCES'][fines_inst_normal]
    inst_code = app.config['ALMA_INSTANCES_NEW'][inst_normal]['code']
    params = {
              'apikey':api_key,
              'source_user_id':uid,
              'source_institution_code':inst_code,
              'format':'json'
             }
    r = requests.get(app.config['ALMA_API'] +
                     app.config['USERS_RESOURCE'], 
                     params=params)
    if r.status_code == 400:
        return r.status_code
    elif r.raise_for_status():
        return r.raise_for_status()
    response = r.json()
    if response['total_record_count'] > 1:
        return 'error for more than one linked acct'
    else:
        return response['user'][0]

def _pay_single_fee(inst, link, amount):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]
    headers = {'Authorization' : 'apikey {}'.format(api_key)}
    params = {
              'op' : 'pay',
              'method' : 'ONLINE',
              'amount' : amount,
              'format' : 'json'}
    r = requests.post(link, params=params, headers=headers)
    return r.json()

if __name__ == "__main__":
    #app.run(debug=True,host='0.0.0.0:8383')
    app.run(debug=True)
