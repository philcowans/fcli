'''Entry point into fcli application'''
import json
import os
import sys
import textwrap

from bs4 import BeautifulSoup
import requests

from .analytics import Ratings
from .config import Config
from .post import Post
from .post_list import PostList
from .state import state_filename, cache_base, staging_base, processed_base

if sys.argv[1] == 'sync':
    config = Config(os.environ['HOME'] + '/.config/fcli/config.ini')
    server = config.mastodon_server()
    client_id = config.mastodon_client_id()
    client_secret = config.mastodon_client_secret()
    auth_url = (
        f'https://{server}/oauth/authorize'
        f'?client_id={client_id}'
        '&scope=read'
        '&redirect_uri=urn:ietf:wg:oauth:2.0:oob'
        '&response_type=code'
    )

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
        timeout=60
    )

    token = response.json()['access_token']
    print(f'Token is {token}')

    with open(state_filename(), encoding='utf-8') as f:
        state = json.load(f)

    max_id = state['max_id']

    num_fetched = 20 # pylint: disable=invalid-name

    while num_fetched > 0:
        url = f'https://{server}/api/v1/timelines/home?min_id={max_id}'
        print(f'Downloading from {url}')
        response = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {token}',
            },
            timeout=60
        )

        responses = response.json()
        num_fetched = len(responses)
        for response in responses:
            response_id = response['id']
            max_id = max([max_id, int(response_id)])
            with open(f'{cache_base()}/{response_id}.json', 'w', encoding='utf-8') as f:
                json.dump(response, f)
        print(f'Suucessfully downloaded {num_fetched} entries')


    with open(state_filename(), 'w', encoding='utf-8') as f:
        json.dump({
            'max_id': max_id
        }, f)

elif sys.argv[1] == 'review':
    post_list = PostList()
    post_list.plan()
    files = post_list.get_filenames()

    for i, file in enumerate(files):
        post = Post.from_file(f'{staging_base()}/{file}')
        print(chr(27) + "[2J")
        print(f'# Next Post ({i+1} of {len(files)})')
        print(f'{post.display_name()} ({post.full_account_name()})')
        print(post.url())
        print('')
        print('## Content')
        print(textwrap.fill(BeautifulSoup(post.content(), features='lxml').get_text(), 80))
        print('')
        if post.reblog_content():
            print('## Reblog')
            print(textwrap.fill(
                 BeautifulSoup(post.reblog_content(), features='lxml').get_text(),
                 80
            ))
            print('')
        if len(post.content_links()) > 0:
            print('## Links')
            for url in post.content_links():
                print(url)
            print('')
        if len(post.media_links()) > 0:
            print('## Attachments')
            for url in post.media_links():
                print(url)
            print('')
        action = input(
            'Action? (A)ctionable / (I)nteresting / (N)ot interesting / (U)nsure / (S)ource '
        )
        if action == 'a':
            os.rename(f'{staging_base()}/{file}', f'{processed_base()}/actionable/{file}')
        if action == 'i':
            os.rename(f'{staging_base()}/{file}', f'{processed_base()}/interesting/{file}')
        if action == 'n':
            os.rename(f'{staging_base()}/{file}', f'{processed_base()}/not_interesting/{file}')
        if action == 's':
            print(post)
            print('')
            action = input(
                'Action? (A)ctionable / (I)nteresting / (N)ot interesting / (U)nsure / (S)ource '
            )
            if action == 'a':
                os.rename(f'{staging_base()}/{file}', f'{processed_base()}/actionable/{file}')
            if action == 'i':
                os.rename(f'{staging_base()}/{file}', f'{processed_base()}/interesting/{file}')
            if action == 'n':
                os.rename(f'{staging_base()}/{file}', f'{processed_base()}/not_interesting/{file}')

elif sys.argv[1] == 'stats':
    Ratings().account_summary().write_lists()

elif sys.argv[1] == 'actions':
    files = list(os.listdir(f'{processed_base()}/actionable'))
    for file in files:
        with open(f'{processed_base()}/actionable/{file}', encoding='utf--8') as f:
            post = json.load(f)
        name = post['account']['display_name']
        title = f'Mastodon action: {name}'
        note = textwrap.fill(BeautifulSoup(post['content'], features='lxml').get_text(), 80) # pylint: disable=invalid-name
        media_attachments = post['media_attachments']
        if post['reblog']:
            note += '\n## Reblog\n'
            note += textwrap.fill(
                BeautifulSoup(post['reblog']['content'], features='lxml').get_text(), 80
            )
            media_attachments += post['reblog']['media_attachments']
        if len(media_attachments) > 0:
            note += '\n## Attachments\n'
            for a in media_attachments:
                note += a['url'] + '\n'
        config = Config(os.environ['HOME'] + '/.config/fcli/config.ini')
        everdo_key = config.everdo_key()
        r = requests.post(
            f'https://localhost:11111/api/items?key={everdo_key}',
            json={'title': title, 'note': note},
            verify=False,
            timeout=60
        )
        print(r.status_code)
