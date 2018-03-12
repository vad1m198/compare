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
            rest_main_org = RESTApi(session[SF_DEF_TOKEN_NAME],session[SF_DEF_INSTANCE_URL_TOKEN_NAME], API_VERSION)
            main_org_user_info = rest_main_org.rest_api_get("/services/oauth2/userinfo")
            if main_org_user_info.status_code == 403:
                session.pop(SF_DEF_TOKEN_NAME, None)
                session.pop(SF_DEF_INSTANCE_URL_TOKEN_NAME, None)
                return redirect(url_for('index'))

            rest_sec_org = RESTApi(session[SF_SEC_TOKEN_NAME],session[SF_SEC_INSTANCE_URL_TOKEN_NAME], API_VERSION)
            sec_org_user_info = rest_sec_org.rest_api_get("/services/oauth2/userinfo")
            if sec_org_user_info.status_code == 403:
                session.pop(SF_SEC_TOKEN_NAME, None)
                session.pop(SF_SEC_INSTANCE_URL_TOKEN_NAME, None)
                return redirect(url_for('index'))
            return f(rest_main_org, main_org_user_info, rest_sec_org, sec_org_user_info, *args, **kwargs)
        else:
            return redirect(url_for('index'))
    return decorated_function

@app.route('/')
def index():
    main_org_user_info = None
    sec_org_user_info = None
    if SF_DEF_TOKEN_NAME in session and SF_DEF_INSTANCE_URL_TOKEN_NAME in session:
        rest_main_org = RESTApi(session[SF_DEF_TOKEN_NAME],session[SF_DEF_INSTANCE_URL_TOKEN_NAME], API_VERSION)
        main_org_user_info = rest_main_org.rest_api_get("/services/oauth2/userinfo")        
        if main_org_user_info.status_code == 403:
            session.pop(SF_DEF_TOKEN_NAME, None)
            return redirect(url_for('index'))
        elif main_org_user_info.status_code != 200:
            return jsonify(main_org_user_info.json())

    if SF_SEC_TOKEN_NAME in session and SF_SEC_INSTANCE_URL_TOKEN_NAME in session:
        rest_sec_org = RESTApi(session[SF_SEC_TOKEN_NAME],session[SF_SEC_INSTANCE_URL_TOKEN_NAME], API_VERSION)
        sec_org_user_info = rest_sec_org.rest_api_get("/services/oauth2/userinfo")        
        if sec_org_user_info.status_code == 403:
            session.pop(SF_SEC_TOKEN_NAME, None)
            return redirect(url_for('index'))
        elif sec_org_user_info.status_code != 200:
            return jsonify(sec_org_user_info.json())
        
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
        session[SF_DEF_TOKEN_NAME] = response.json().get('access_token')
        session[SF_DEF_INSTANCE_URL_TOKEN_NAME] = response.json().get('instance_url')
        return redirect(url_for('index'))
    else:
        session[SF_SEC_TOKEN_NAME] = response.json().get('access_token')
        session[SF_SEC_INSTANCE_URL_TOKEN_NAME] = response.json().get('instance_url')
        return redirect(url_for('index'))

@app.route('/compare/classes',methods=['GET'])
@login_required
def compare_classes(rest_main_org, main_org_user_info, rest_sec_org, sec_org_user_info):    
    query_url = main_org_user_info.json()['urls']['tooling_rest'] +\
        'query/?q=' +\
        quote('SELECT Id,Name,ManageableState from ApexClass WHERE ManageableState=\'unmanaged\' ORDER BY NAME ASC LIMIT 1000') 
    resp = rest_main_org.rest_api_get(query_url)
    if resp.status_code == 200:
        return render_template('compare_classes.html', options=resp.json()['records'])
    else:
        return jsonify(resp.json())

@app.route("/compare/classes", methods=['POST'])
@login_required
def compare_classes_post(rest_main_org, main_org_user_info, rest_sec_org, sec_org_user_info):
    names =request.form.getlist('classes')
    return redirect(url_for("compare_classes_results", class_names=','.join(names)))

@app.route("/compare/classes_result", methods=['GET'])
@login_required
def compare_classes_results(rest_main_org, main_org_user_info, rest_sec_org, sec_org_user_info):
    class_names_param = request.args['class_names']
    class_names = "'"+"','".join(class_names_param.split(","))+"'"
    
    query_url_one = main_org_user_info.json()['urls']['tooling_rest'] +\
        'query/?q=' +\
        quote('SELECT Name,Body,ManageableState from ApexClass WHERE Name IN (' + class_names + ') AND ManageableState=\'unmanaged\' ORDER BY NAME ASC')
    resp_one = rest_main_org.rest_api_get(query_url_one)

    query_url_two = sec_org_user_info.json()['urls']['tooling_rest'] +\
        'query/?q=' +\
        quote('SELECT Name,Body,ManageableState from ApexClass WHERE Name IN (' + class_names + ') AND ManageableState=\'unmanaged\' ORDER BY NAME ASC')
    resp_two = rest_sec_org.rest_api_get(query_url_two)
    
    if resp_one.status_code == 200 and resp_two.status_code == 200:
        resp_one_map = dict((r['Name'],r['Body']) for r in resp_one.json().get('records'))
        resp_two_map = dict((r['Name'],r['Body']) for r in resp_two.json().get('records'))
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

@app.route("/compare/aura", methods=['GET'])
@login_required
def compare_aura(rest_main_org, main_org_user_info, rest_sec_org, sec_org_user_info):
    query_url = main_org_user_info.json()['urls']['tooling_rest'] +\
        'query/?q=' +\
         quote('SELECT Id,ApiVersion,Description,DeveloperName,Language'\
            ',MasterLabel,ManageableState from AuraDefinitionBundle WHERE  ManageableState=\'unmanaged\' ORDER BY DeveloperName ASC LIMIT 1000')
    resp = rest_main_org.rest_api_get(query_url)
    if resp.status_code == 200:
        return render_template('compare_aura.html', options=resp.json()['records'])
    else:
        return jsonify(resp.json())

@app.route("/compare/aura", methods=['POST'])
@login_required
def compare_aura_post(rest_main_org, main_org_user_info, rest_sec_org, sec_org_user_info):    
    names = request.form.getlist('components')
    return redirect(url_for("compare_aura_results", component_names=','.join(names)))

@app.route("/compare/aura_result", methods=['GET'])
@login_required
def compare_aura_results(rest_main_org, main_org_user_info, rest_sec_org, sec_org_user_info):
    component_names_param = request.args['component_names']
    component_names = "'"+"','".join(component_names_param.split(","))+"'"
    
    query_url_one = main_org_user_info.json()['urls']['tooling_rest'] +\
        'query/?q=' +\
            quote('SELECT AuraDefinitionBundle.DeveloperName,AuraDefinitionBundleId,DefType'\
            ',ManageableState,Source from AuraDefinition WHERE AuraDefinitionBundle.DeveloperName IN (' + component_names + ')'\
            ' AND ManageableState=\'unmanaged\' AND DefType NOT IN (\'DOCUMENTATION\',\'SVG\') '\
            ' ORDER BY AuraDefinitionBundle.DeveloperName ASC')
    resp_one = rest_main_org.rest_api_get(query_url_one)

    query_url_two = sec_org_user_info.json()['urls']['tooling_rest'] +\
        'query/?q=' +\
        quote('SELECT AuraDefinitionBundle.DeveloperName,AuraDefinitionBundleId,DefType'\
            ',ManageableState,Source from AuraDefinition WHERE AuraDefinitionBundle.DeveloperName IN (' + component_names + ')'\
            ' AND ManageableState=\'unmanaged\' AND DefType NOT IN (\'DOCUMENTATION\',\'SVG\') '\
            ' ORDER BY AuraDefinitionBundle.DeveloperName ASC')
    resp_two = rest_sec_org.rest_api_get(query_url_two)
    
    if resp_one.status_code == 200 and resp_two.status_code == 200:
        resp_one_map = dict((r['AuraDefinitionBundle']['DeveloperName'] + r['DefType'],r['Source']) for r in resp_one.json().get('records'))
        resp_two_map = dict((r['AuraDefinitionBundle']['DeveloperName'] + r['DefType'],r['Source']) for r in resp_two.json().get('records'))
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
        return render_template('compare_aura_results.html', result=result)  
    else:
        if resp_one.status_code != 200:
            return jsonify(resp_one.json())
        if resp_two.status_code != 200:
            return jsonify(resp_two.json())


	
if __name__ == "__main__":
	app.run()