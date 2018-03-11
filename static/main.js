$(document).ready(function () {

	$('#main-login').click(function() {
		var oauthUrl = "https://login.salesforce.com"
		if ( $('#org_one_env').val() == 'Sandbox' ) {			
			var oauthUrl = "https://test.salesforce.com"
		}
		var clientid = $("#client-id").val()
		var baseHostUrl = location.protocol + '//' + location.host;
		var callBackUrl = baseHostUrl + "/auth/authorized";
		var state = {
			org: 'main',
			type: $('#org_one_env').val()
		}
		oauthUrl += "/services/oauth2/authorize?" +
			"response_type=code&client_id=" + clientid +
			"&prompt=login" +
			"&redirect_uri=" + callBackUrl + "&state=" + btoa(JSON.stringify(state));

		window.location =  oauthUrl;

	})

	$('#secondary-login').click(function() {
		var oauthUrl = "https://login.salesforce.com"
		if ( $('#org_env').val() == 'Sandbox' ) {			
			var oauthUrl = "https://test.salesforce.com"
		}
		var clientid = $("#client-id").val()
		var baseHostUrl = location.protocol + '//' + location.host;
		var callBackUrl = baseHostUrl + "/auth/authorized";
		var state = {
			org: 'secondary',
			type: $('#org_env').val()
		}
		console.log('state >>>>>>>>>>>> ');
		console.log(state);
		oauthUrl += "/services/oauth2/authorize?" +
			"response_type=code&client_id=" + clientid +
			"&prompt=login" +
			"&redirect_uri=" + callBackUrl + "&state=" + btoa(JSON.stringify(state));

		window.location =  oauthUrl;

	})
		
})