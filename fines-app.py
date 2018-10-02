from flask import Flask, redirect, request, render_template, request, url_for
import settings
import json
import requests

app = Flask(__name__)

app.config['ALMA_API'] = settings.ALMA_API
app.config['ALMA_INSTANCES'] = settings.ALMA_INSTANCES
app.config['INST_MAP'] = settings.INST_MAP

@app.route('/')
def index():
    return render_template('index.html',
                           institutions=app.config['ALMA_INSTANCES'].keys())

@app.route('/user', methods=['GET', 'POST'])
def user():
    if request.method == 'GET':
        return('there no get method defined yet')
    else:
        fines = _get_fines(request.form['inst'], request.form['uid'])
        user = _get_user(request.form['inst'], request.form['uid'])
        if user == 400:
            return render_template('user_not_found.html',
                                   inst=request.form['inst'],
                                   uid=request.form['uid'])
        else:
            return render_template('user.html',
                                   fines=fines,
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
    result = _get_single_fine('scf', 'ihardy', '3297895250004617')
    return result

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
                     'v1/users/{}/fees'.format(uid) + 
                     '?apikey={}&status=ACTIVE&format=json'.format(api_key))
    return r.json()

def _get_single_fine(inst, uid, fee_id):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]
    r = requests.get(app.config['ALMA_API'] +
                     'v1/users/{}/fees/{}'.format(uid, fee_id) +
                     '?apikey={}&format=json'.format(api_key))
    return r.json()

def _get_user(inst, uid):
    inst_normal = _resolve_inst(inst)
    api_key = app.config['ALMA_INSTANCES'][inst_normal]
    r = requests.get(app.config['ALMA_API'] +
                     'v1/users/{}'.format(uid) + 
                     '?apikey={}&format=json'.format(api_key))
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
    r = requests.post(app.config['ALMA_API'] +
                      'v1/users/{}/fees/{}'.format(uid, fee_id) +
                      '?op=pay&method=ONLINE&amount={}'.format(amount) +
                      '&format=json',
                      headers=headers)
    return r.json()



app.run(debug=True,host='0.0.0.0')
