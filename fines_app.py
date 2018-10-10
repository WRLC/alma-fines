from flask import (Flask, redirect, request, render_template,
    request, session, url_for)
from functools import wraps
import json
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

@app.route('/login/placeholder', methods=['POST'])
def test_login():
    if 'username' in session:
        return redirect(url_for('index'))
    else:
        session['username'] = request.form['user-name']
        session['user_home'] = app.config['TEST_USERS'][session['username']]
        return redirect(url_for('index'))

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
        lender = request.form['lending-inst']
        uid = request.form['uid']
        linked_account = _get_linked_user(session['user_home'], 
                                          lender, 
                                          uid)
        if linked_account == 400:
            return render_template('user_not_found.html',
                                   inst=lender,
                                   uid=uid)
        else:
            lending_name = app.config['ALMA_INSTANCES_NEW'][lender]['name']
            fees = []
            fines = _get_fines(request.form['lending-inst'], linked_account['primary_id'])
            if fines['total_record_count'] > 0:
                for fee in fines['fee']:
                    fees.append(fee)
                return render_template('user_fines.html',
                                       home=session['user_home'],
                                       fees=fees,
                                       lending_name=lending_name,
                                       user=linked_account)
            else:
                return render_template('user_no_fines.html',
                                        user=linked_account)

@app.route('/payment', methods=['POST'])
@auth_required
def payment():
    payment_queue = []
    payments = []
    for k in request.form:
        fee_data = json.loads(request.form[k].replace("'", '"'))
        fee_details = _get_single_fine(fee_data['owner'].lower(),
                                       fee_data['user'],
                                       fee_data['fee_id'])
        payment_queue.append(fee_details)

    for payment in payment_queue:
        payment_result = _pay_single_fee(payment['owner']['value'].lower(),
                                         payment['user_primary_id']['value'],
                                         payment['id'],
                                         str(payment['balance']))
        audit_log.info(
            '{staff_id}\t{accepted_at}\t{t_id}\t{amount}\t{owner}'.format(staff_id=session['username'],
                                                                          accepted_at=session['user_home'],
                                                                          t_id=payment_result['id'],
                                                                          amount=payment_result['transaction'][0]['amount'],
                                                                          owner=payment_result['owner']['value']))
        #payments.append(payment_result)
        payments.append(json.dumps(payment_result, sort_keys=True, indent=4))

    return render_template('payment.html',
                           payments=payments)

@app.route('/test', methods=['GET', 'POST'])
@auth_required
def test():
    return json.dumps(request.cookies)

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

def _pay_single_fee(inst, uid, fee_id, amount):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]
    headers = {'Authorization' : 'apikey {}'.format(api_key)}
    params = {
              'op' : 'pay',
              'method' : 'ONLINE',
              'amount' : amount,
              'format' : 'json'}
    r = requests.post(app.config['ALMA_API'] +
                      app.config['FEE_RESOURCE'].format(uid, fee_id), 
                      params=params,
                      headers=headers)
    return r.json()


if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0')
