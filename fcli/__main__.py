'''Entry point into fcli application'''
import json
import os
import subprocess
import sys
import textwrap

from bs4 import BeautifulSoup
import requests

from .analytics import Ratings
from .config import Config
from .mastodon_api import accounts_following, accounts_lookup
from .post import Post
from .post_list import PostList
from .state import following_filename, state_filename, cache_base, staging_base, processed_base, outbox_base, sent_base

def _do_sync():
    print('Authenticating ...')
    config = Config(os.environ['HOME'] + '/.config/fcli/config.ini')
    server = config.mastodon_server()
    username = config.mastodon_username()
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
        f'https://{server}/oauth/token',
        data=form_data,
        timeout=60
    )

    token = response.json()['access_token']
    user_id = accounts_lookup(username, server=server, token=token)['id']
    print('')
    print('done.')
    print('Synchronising following list ... ', end='')
    following = accounts_following(user_id, server=server, token=token)
    with open(following_filename(), 'w', encoding='utf-8') as f:
        json.dump(following, f)
    print('done.')
    print('Posting queued statuses ... ', end='')
    for file in os.listdir(outbox_base()):
        with open(outbox_base() + '/' + file, 'r') as f:
            content = f.read()

        form_data = {
            'status': content,
            'visibility': 'public',
            'language': 'en',
        }

        response = requests.post(
            f'https://{server}/api/v1/statuses',
            headers={
                'Authorization': f'Bearer {token}',
            },
            data=form_data,
            timeout=60
        )

        os.rename(f'{outbox_base()}/{file}', f'{sent_base()}/{file}')
    print('done.')
    print('Fetching new posts ... ', end='')
    with open(state_filename(), encoding='utf-8') as f:
        state = json.load(f)

    max_id = state['max_id']

    num_fetched = 20 # pylint: disable=invalid-name

    while num_fetched > 0:
        url = f'https://{server}/api/v1/timelines/home?min_id={max_id}'
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

    with open(state_filename(), 'w', encoding='utf-8') as f:
        json.dump({
            'max_id': max_id
        }, f)
    print('done.')

def _do_actions():
    print('Sending actions to Everdo ... ', end='')
    files = list(os.listdir(f'{processed_base()}/actionable'))
    for file in files:
        post = Post.from_file(f'{processed_base()}/actionable/{file}')
        name = post.display_name()
        title = f'Mastodon action: {name}'
        note = post.text_for_action()
        config = Config(os.environ['HOME'] + '/.config/fcli/config.ini')
        everdo_key = config.everdo_key()
        r = requests.post(
            f'https://localhost:11111/api/items?key={everdo_key}',
            json={'title': title, 'note': note},
            verify=False,
            timeout=60
        )
        os.rename(f'{processed_base()}/actionable/{file}', f'{processed_base()}/actioned/{file}')
    print('done.')

if (len(sys.argv) == 1) or (sys.argv[1] == 'review'):
    print('Updating stats ... ', end='')
    Ratings().account_summary().write_lists()
    print('done.')
    _do_sync()

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
        finished = False # pylint: disable=invalid-name
        while not finished:
            action = input(
                'Action? (A)ctionable / (B)oost / (I)nteresting / (N)ot interesting / '
                '(U)nsure / (S)ource / (O)pen'
            )
            if action == 'a':
                os.rename(f'{staging_base()}/{file}', f'{processed_base()}/actionable/{file}')
                finished = True # pylint: disable=invalid-name
            if action == 'b':
                os.rename(f'{staging_base()}/{file}', f'{processed_base()}/boostable/{file}')
                finished = True # pylint: disable=invalid-name
            if action == 'i':
                os.rename(f'{staging_base()}/{file}', f'{processed_base()}/interesting/{file}')
                finished = True # pylint: disable=invalid-name
            if action == 'n':
                os.rename(f'{staging_base()}/{file}', f'{processed_base()}/not_interesting/{file}')
                finished = True # pylint: disable=invalid-name
            if action == 's':
                print(post)
                print('')
            if action == 'o':
                link_type = input('Link type? (L)ink / (A)ttachment')
                link_index = int(input('Link number? (Zero indexed)'))
                if link_type == 'l':
                    url = post.content_links()[link_index]
                elif link_type == 'a':
                    url = post.media_links()[link_index]
                subprocess.run(['open', url], check=False)

    _do_actions()
    files = list(os.listdir(f'{cache_base()}'))
    for file in files:
        os.rename(f'{cache_base()}/{file}', f'{processed_base()}/skipped/{file}')
elif sys.argv[1] == 'sync':
    _do_sync()

elif sys.argv[1] == 'prompt':
    files = list(os.listdir(cache_base()))
    for file in files:
        post = Post.from_file(f'{cache_base()}/{file}')
        print('# Post')
        print('## URL')
        print(post.url())
        print('')
        if post.content():
            print('## Content')
            print(textwrap.fill(BeautifulSoup(post.content(), features='lxml').get_text(), 80))
            print('')
        if post.reblog_content():
            print('## Reblog Content')
            print(textwrap.fill(
                 BeautifulSoup(post.reblog_content(), features='lxml').get_text(),
                 80
            ))
            print('')


elif sys.argv[1] == 'stats':
    Ratings().account_summary().write_lists()

elif sys.argv[1] == 'actions':
    _do_actions()
