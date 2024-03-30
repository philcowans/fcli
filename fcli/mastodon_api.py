import re

import requests

def accounts_following(user_id, server, token):
    url = _base_url(server) + f'/accounts/{user_id}/following'
    print(f'Fetching accounts from URL {url}')
    return _paginated_response(url, token=token)

def accounts_lookup(username, server, token):
    url = _base_url(server) + f'/accounts/lookup?acct={username}'
    return _authenticated_response(url, token=token)

def _authenticated_response(url, token):
    response = requests.get(
        url,
        headers={
            'Authorization': f'Bearer {token}',
        },
        timeout=60
    )  
    return response.json()

def _paginated_response(url, token):
    results = []
    while url is not None:
        response = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {token}',
            },
            timeout=60
        )  
        results += response.json()
        print(f'Response length: {len(response.json())}')
        if 'link' in response.headers:
            links = {
                re.match('rel="(.*)"', l[1])[1]: re.match('<(.*)>', l[0])[1]
                for l in [
                    c.split('; ') for c in response.headers['link'].split(', ')
                ]
            }
            print(f'Headers: {links}')
            url = links.get('next')
        else:
            url = None
    return results

def _base_url(server):
    return f'https://{server}/api/v1' 
