from flask import (Flask, redirect, request, render_template,
    request, session, url_for)
import settings
import json
import requests

app = Flask(__name__)

app.config['ALMA_API'] = settings.ALMA_API
app.config['ALMA_INSTANCES'] = settings.ALMA_INSTANCES
app.config['INST_MAP'] = settings.INST_MAP
app.config['SESSION_KEY']= settings.SESSION_KEY
app.config['FEE_RESOURCE'] = 'almaws/v1/users/{}/fees/{}'
app.config['FEES_RESOURCE'] = 'almaws/v1/users/{}/fees'
app.config['USER_RESOURCE'] = 'almaws/v1/users/{}'

app.secret_key = app.config['SESSION_KEY']

@app.route('/')
def index():
    session['username'] = 'hardy'
    return render_template('index.html',
                           institutions=app.config['ALMA_INSTANCES'].keys())

@app.route('/user', methods=['GET', 'POST'])
def user():
    if request.method == 'GET':
        return('there no get method defined yet')
    else:
        user = _get_user(request.form['inst'], request.form['uid'])
        if user == 400:
            return render_template('user_not_found.html',
                                   inst=request.form['inst'],
                                   uid=request.form['uid'])
        else:
            fees = []
            fines = _get_fines(request.form['inst'], request.form['uid'])

            for fee in fines['fee']:
                fees.append(fee)
            return render_template('user.html',
                                   fees=fees,
                                   user=user)


@app.route('/payment', methods=['POST'])
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
        #payments.append(payment_result)
        payments.append(json.dumps(payment_result, sort_keys=True, indent=4))

    return render_template('payment.html',
                           payments=payments)

@app.route('/test', methods=['GET', 'POST'])
def test():
    result = []
    for k in request.form:
        result.append(request.form[k])
    return(json.loads(result[0])['link'])

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



app.run(debug=True,host='0.0.0.0')
