# _author_ = "Jean-Claude Tissier"
# _github_ = "https://github.com/jctissier/Salesforce-Oauth2-REST-Metadata-API-Python-Examples"

import requests
#import salesforce_username_password_flow as oauth


class RESTApi(object):
    """
        Salesforce REST API Class
            -Include HTTP Methods:      (Working)           GET, POST, HEAD
            -Remaining methods:         (Not Tested)        PUT, PATCH, DELETE
            -Authenticated headers are required to call Salesforce's REST API
                -example for authenticated headers
                {
                    'Content-Type': 'application/json',
                    'X-PrettyPrint': '1',
                    'Authorization': 'Bearer "access_token"'
                }
    """

    def __init__(self, access_token, instance_url, api_version):
        """
        Constructor for RESTApi Class
        :param rest_url: particular API method that needs to be called,
                   ex: sobjects in ==> org_instance/services/data/v39.0/sobjects
        :param body: used for the body of API calls (ex: POST)
        :param version: Salesforce API version (ex: current is '39.0')
        """
        self.instance = instance_url
        self.api_version = api_version
        self.sf_headers = {
                    'Content-Type': 'application/json',
                    'X-PrettyPrint': '1',
                    'Authorization': 'Bearer ' + access_token
                }

    def rest_api_get(self, rest_url):
        """
        GET request to the REST API
        :return: JSON string of the GET response
        """
        if rest_url.startswith('http:') or rest_url.startswith('https:'):
            response = requests.get(
                "{rest_url}".format(
                    org_instance=self.instance, rest_url=rest_url
                ).replace("{version}", self.api_version),
                headers=self.sf_headers
            )
        else:    
            response = requests.get(
                "{org_instance}/{rest_url}".format(
                    org_instance=self.instance, rest_url=rest_url
                ).replace("{version}", self.api_version),
                headers=self.sf_headers
            )

        return response
