from bs4 import BeautifulSoup

import json
import numpy as np
import os
import requests
import sys
import textwrap

if sys.argv[1] == 'sync':
    server = os.environ['MASTODON_SERVER']
    client_id = os.environ['MASTODON_CLIENT_ID']
    client_secret = os.environ['MASTODON_CLIENT_SECRET']
    auth_url = f'https://{server}/oauth/authorize?client_id={client_id}&scope=read&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code'

    code = input(f'Please visit\n\n{auth_url}\n\nand past code here: ')

    form_data = {
        'client_id': client_id, 
        'client_secret': client_secret,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'grant_type': 'authorization_code',
        'code': code,
        'scope': 'read',
    }

    response = requests.post(
        f'https://{server}/oauth/token',
        data=form_data,
    )

    token = response.json()['access_token']
    print(f'Token is {token}')

    with open('state.json') as f:
        state = json.load(f)

    max_id = state['max_id']

    num_fetched = 20

    while num_fetched > 0:
        url = f'https://{server}/api/v1/timelines/home?min_id={max_id}'
        print(f'Downloading from {url}')
        response = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {token}',
            }
        )

        responses = response.json()
        num_fetched = len(responses)
        for response in responses:
            response_id = response['id']
            max_id = max([max_id, int(response_id)])
            with open(f'cache/{response_id}.json', 'w') as f:
                json.dump(response, f)
        print(f'Suucessfully downloaded {num_fetched} entries')


    with open('state.json', 'w') as f:
        json.dump({
            'max_id': max_id
        }, f)

elif sys.argv[1] == 'review':
    def load_post(filename):
        with open(filename) as f:
            return json.load(f)

    # files = np.random.choice(list(os.listdir('cache')), size=50, replace=False)
    files = [(file, load_post(f'cache/{file}')) for file in os.listdir('cache')]
    files = np.random.choice([file[0] for file in files if file[1]['account']['username'] not in ['benb', 'HamiltonsLive']], size=50, replace=False)
    
    for i, file in enumerate(files):
        post = load_post(f'cache/{file}')
        print('')
        print(f'# Next Post ({i+1} of {len(files)})')
        print(post['account']['display_name'] + ' (' + post['account']['username'] + ')')
        print(post['url'])
        print('')
        print('## Content')
        print(textwrap.fill(BeautifulSoup(post['content'], features='lxml').get_text(), 80))
        print('')
        media_attachments = post['media_attachments']
        if post['reblog']:
            print('## Reblog')
            print(textwrap.fill(BeautifulSoup(post['reblog']['content'], features='lxml').get_text(), 80))
            print('')
            media_attachments += post['reblog']['media_attachments']
        if len(media_attachments) > 0:
            print('## Attachments')
            for a in media_attachments:
                print(a['url'])
            print('')
        action = input('Action? (A)ctionable / (I)nteresting / (N)ot interesting / (U)nsure / (S)ource ')
        if action == 'a':
            os.rename(f'cache/{file}', f'processed/actionable/{file}')
        if action == 'i':
            os.rename(f'cache/{file}', f'processed/interesting/{file}')
        if action == 'n':
            os.rename(f'cache/{file}', f'processed/not_interesting/{file}')
        if action == 's':
            print(post)
            print('')
            action = input('Action? (A)ctionable / (I)nteresting / (N)ot interesting / (U)nsure / (S)ource ')
            if action == 'a':
                os.rename(f'cache/{file}', f'processed/actionable/{file}')
            if action == 'i':
                os.rename(f'cache/{file}', f'processed/interesting/{file}')
            if action == 'n':
                os.rename(f'cache/{file}', f'processed/not_interesting/{file}')

elif sys.argv[1] == 'stats':
    for status in ['unprocessed', 'actionable', 'interesting', 'not_interesting']:
        if status == 'unprocessed':
            path = 'cache'
        else:
            path = 'processed/' + status
        for file in os.listdir(path):
            with open(f'{path}/{file}') as f:
                post = json.load(f)
            print(','.join([post['created_at'][:10], post['account']['username'], status]))

elif sys.argv[1] == 'actions':
    files = list(os.listdir('processed/actionable'))
    for file in files:
        with open(f'processed/actionable/{file}') as f:
            post = json.load(f)
        name = post['account']['display_name']
        title = f'Mastodon action: {name}'
        note = textwrap.fill(BeautifulSoup(post['content'], features='lxml').get_text(), 80)
        media_attachments = post['media_attachments']
        if post['reblog']:
            note += '\n## Reblog\n'
            note += textwrap.fill(BeautifulSoup(post['reblog']['content'], features='lxml').get_text(), 80)
            media_attachments += post['reblog']['media_attachments']
        if len(media_attachments) > 0:
            note += '\n## Attachments\n'
            for a in media_attachments:
                note += a['url'] + '\n'
        everdo_key = os.environ['EVERDO_KEY']
        r = requests.post(f'https://localhost:11111/api/items?key={everdo_key}', json={'title': title, 'note': note}, verify=False)
        print(r.status_code)
