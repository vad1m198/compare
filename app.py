from flask import Flask,render_template,request,jsonify,session,redirect,url_for
import os
from config import Config
import requests
import json
from REST_Api_ import RESTApi
from functools import wraps
import base64
from urllib.parse import quote
from diff2html import diff2html as d2h
import diff_match_patch as dmp_module

app = Flask(__name__)
app.config.from_object(Config)
app.debug = True

API_VERSION = os.environ['SALESFORCE_API_VERSION']
CONSUMER_KEY = os.environ['SALESFORCE_CONSUMER_KEY']
CONSUMER_SECRET = os.environ['SALESFORCE_CONSUMER_SECRET']
REDIRECT_URI = os.environ['SALESFORCE_REDIRECT_URI']
SF_DEF_TOKEN_NAME = 'salesforce_def_token'
SF_DEF_INSTANCE_URL_TOKEN_NAME = 'salesforce_def_instance_url'
SF_SEC_TOKEN_NAME = 'salesforce_sec_token'
SF_SEC_INSTANCE_URL_TOKEN_NAME = 'salesforce_sec_instance_url'


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if SF_DEF_TOKEN_NAME in session and SF_DEF_INSTANCE_URL_TOKEN_NAME in session and SF_SEC_TOKEN_NAME in session and SF_SEC_INSTANCE_URL_TOKEN_NAME in session:
            return f(*args, **kwargs)    
        else:
            return redirect(url_for('index'))
    return decorated_function
"""
def secondary_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if SF_SEC_TOKEN_NAME in session and SF_SEC_INSTANCE_URL_TOKEN_NAME in session and SF_DEF_TOKEN_NAME in session and SF_DEF_INSTANCE_URL_TOKEN_NAME in session:
            return f(*args, **kwargs)    
        elif SF_DEF_TOKEN_NAME in session and SF_DEF_INSTANCE_URL_TOKEN_NAME in session:
            return redirect(url_for('compare'))
        else:
            return redirect(url_for('index'))
    return decorated_function
"""


@app.route('/')
def index():
    main_org_user_info = None
    sec_org_user_info = None
    if SF_DEF_TOKEN_NAME in session and SF_DEF_INSTANCE_URL_TOKEN_NAME in session:
        rest_main_org = RESTApi(session[SF_DEF_TOKEN_NAME],session[SF_DEF_INSTANCE_URL_TOKEN_NAME], API_VERSION)
        main_org_user_info = rest_main_org.rest_api_get("/services/oauth2/userinfo")
    
    if SF_SEC_TOKEN_NAME in session and SF_SEC_INSTANCE_URL_TOKEN_NAME in session:
        rest_sec_org = RESTApi(session[SF_SEC_TOKEN_NAME],session[SF_SEC_INSTANCE_URL_TOKEN_NAME], API_VERSION)
        sec_org_user_info = rest_sec_org.rest_api_get("/services/oauth2/userinfo")
    
    return render_template('index.html', main_org_user_name = None if main_org_user_info is None else main_org_user_info.json().get('name'),
                    sec_org_user_name = None if sec_org_user_info is None else sec_org_user_info.json().get('name'),
                    client_key=CONSUMER_KEY)
        
@app.route('/logout')
def logout():
    if request.args.get('org') == 'main':
        session.pop(SF_DEF_TOKEN_NAME, None)
        session.pop(SF_DEF_INSTANCE_URL_TOKEN_NAME, None)
        return redirect(url_for('index'))
    else:
        session.pop(SF_SEC_TOKEN_NAME, None)
        session.pop(SF_SEC_INSTANCE_URL_TOKEN_NAME, None)
        return redirect(url_for('index'))

@app.route('/auth/authorized')
def authorized():
    body = {
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'code': request.args.get('code'),
            'client_id': CONSUMER_KEY,
            'client_secret': CONSUMER_SECRET
        }

    d = json.loads(base64.b64decode(request.args.get('state')))

    if d.get('type').lower() == 'sandbox':
        auth_site = 'https://test.salesforce.com'
    else:
        auth_site = 'https://login.salesforce.com'

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(
        "{site}{token_url}".format(
            site=auth_site,
            token_url="/services/oauth2/token"
        ),
        data=body,
        headers=headers
    )
    if response is None or response.json().get('access_token') is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error'],
            request.args['error_description']            
        )

    if d['org'] == 'main':
        session[SF_DEF_TOKEN_NAME] = response.json()['access_token']
        session[SF_DEF_INSTANCE_URL_TOKEN_NAME] = response.json()['instance_url']
        return redirect(url_for('index'))
    else:
        session[SF_SEC_TOKEN_NAME] = response.json()['access_token']
        session[SF_SEC_INSTANCE_URL_TOKEN_NAME] = response.json()['instance_url']
        return redirect(url_for('index'))

    
"""
@app.route('/u')
@login_required
def user_info():
    if request.args.get('org') == 'main':
        rest = RESTApi(session[SF_DEF_TOKEN_NAME],session[SF_DEF_INSTANCE_URL_TOKEN_NAME], API_VERSION)
    else:
        rest = RESTApi(session[SF_SEC_TOKEN_NAME],session[SF_SEC_INSTANCE_URL_TOKEN_NAME], API_VERSION)    
    user_info = rest.rest_api_get("/services/oauth2/userinfo")
    return jsonify(user_info.json())

@app.route('/compare')
@login_required
def compare():
    if SF_SEC_TOKEN_NAME in session and SF_SEC_INSTANCE_URL_TOKEN_NAME in session:
        rest = RESTApi(session[SF_SEC_TOKEN_NAME],session[SF_SEC_INSTANCE_URL_TOKEN_NAME], API_VERSION)
        user_info = rest.rest_api_get("/services/oauth2/userinfo")
        return render_template('compare.html', user_name = user_info.json()['name'])
    else:
        return render_template('compare.html',client_key=CONSUMER_KEY)
"""
@app.route('/compare/classes',methods=['GET'])
@login_required
def compare_classes():
    rest = RESTApi(session[SF_DEF_TOKEN_NAME],session[SF_DEF_INSTANCE_URL_TOKEN_NAME], API_VERSION)
    user_info = rest.rest_api_get("/services/oauth2/userinfo")
    query_url = user_info.json()['urls']['tooling_rest'] +\
        'query/?q=' +\
        quote('SELECT Id,Name,ManageableState from ApexClass WHERE ManageableState=\'unmanaged\' ORDER BY NAME ASC LIMIT 1000') 
    resp = rest.rest_api_get(query_url)
    if resp.status_code == 200:
        return render_template('compare_classes.html', options=resp.json()['records'])
    else:
        return jsonify(resp.json())

@app.route("/compare/classes", methods=['POST'])
@login_required
def compare_classes_post():
    names =request.form.getlist('classes')
    return redirect(url_for("compare_classes_results", class_names=','.join(names)))

@app.route("/compare/classes_result", methods=['GET'])
@login_required
def compare_classes_results():
    class_names_param = request.args['class_names']
    class_names = "'"+"','".join(class_names_param.split(","))+"'"
    
    rest_one = RESTApi(session[SF_DEF_TOKEN_NAME],session[SF_DEF_INSTANCE_URL_TOKEN_NAME], API_VERSION)
    user_info_one = rest_one.rest_api_get("/services/oauth2/userinfo")
    rest_two = RESTApi(session[SF_SEC_TOKEN_NAME],session[SF_SEC_INSTANCE_URL_TOKEN_NAME], API_VERSION)
    user_info_two = rest_two.rest_api_get("/services/oauth2/userinfo")

    query_url_one = user_info_one.json()['urls']['tooling_rest'] +\
        'query/?q=' +\
        quote('SELECT Name,Body,ManageableState from ApexClass WHERE Name IN (' + class_names + ') AND ManageableState=\'unmanaged\' ORDER BY NAME ASC')
    resp_one = rest_one.rest_api_get(query_url_one)

    query_url_two = user_info_two.json()['urls']['tooling_rest'] +\
        'query/?q=' +\
        quote('SELECT Name,Body,ManageableState from ApexClass WHERE Name IN (' + class_names + ') AND ManageableState=\'unmanaged\' ORDER BY NAME ASC')
    resp_two = rest_two.rest_api_get(query_url_two)
    
    if resp_one.status_code == 200 and resp_two.status_code == 200:
        resp_one_map = dict((r['Name'],r['Body']) for r in resp_one.json()['records'])
        resp_two_map = dict((r['Name'],r['Body']) for r in resp_two.json()['records'])        
        dmp = dmp_module.diff_match_patch()
        result = []
        for key, value in resp_one_map.items():
            body_one = value
            body_two = resp_two_map[key] if  key in resp_two_map else ""
            diff = dmp.diff_main(body_one, body_two)
            diff_present = bool(0)
            for op, length in diff:
                if op != 0: 
                    diff_present = bool(1)
                    break

            if diff_present:
                result_html = d2h(diff)
            else:
                result_html = '<table class="no-diff"><tr>No differences</tr></table>'
            result.append({'name':key, 'result_html' : result_html})
        return render_template('compare_classes_results.html', result=result)  
    else:
        if resp_one.status_code != 200:
            return jsonify(resp_one.json())
        if resp_two.status_code != 200:
            return jsonify(resp_two.json())

"""
@app.route('/compare/aura')
@secondary_login_required
def compare_aura():
    return render_template('compare.html',client_key=CONSUMER_KEY)
"""
	
if __name__ == "__main__":
	app.run()