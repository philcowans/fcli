import requests

class Auth:
    token = None

    @classmethod
    def get_token(cls, state, server, config):
        if cls.token:
            return cls.token

        cls.token = state.get('token')
        if cls.token is not None:
            url = f'https://{server}/api/v1/accounts/verify_credentials'
            response = requests.get(
                url,
                headers={
                    'Authorization': f'Bearer {cls.token}',
                },
                timeout=60
            )
            if response.status_code != 200:
                cls.token = None
        
        if cls.token is None:
            client_id = config.mastodon_client_id()
            client_secret = config.mastodon_client_secret()
            auth_url = (
                f'https://{server}/oauth/authorize'
                f'?client_id={client_id}'
                '&scope=read+write'
                '&redirect_uri=urn:ietf:wg:oauth:2.0:oob'
                '&response_type=code'
            )
            print('')
            print('')
            code = input(f'Please visit\n\n{auth_url}\n\nand past code here: ')

            form_data = {
                'client_id': client_id, 
                'client_secret': client_secret,
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'grant_type': 'authorization_code',
                'code': code,
                'scope': 'read write',
            }

            response = requests.post(
                f'https://{server}/oauth/cls.token',
                data=form_data,
                timeout=60
            )

            cls.token = response.json()['access_cls.token']
            print('')

        return cls.token
