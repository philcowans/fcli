'''Entry point into fcli application'''
from collections import defaultdict
from datetime import datetime
from email.parser import BytesParser
from email.policy import default
from glob import glob
from pathlib import Path
from time import time

import json
import logging
import os
import subprocess
import sys
import textwrap
import urllib3
import re

from bs4 import BeautifulSoup
import requests

from .analytics import Ratings
from .auth import Auth
from .config import Config
from .mastodon_api import accounts_following, accounts_lookup, notifications
from .post import Post
from .post_list import PostList
from .state import filter_filename, following_filename, state_filename, cache_base, staging_base, processed_base, outbox_base, sent_base

logging.captureWarnings(True)

def _do_index():
    with open(filter_filename(), 'r', encoding='utf-8') as f:
        groups = json.load(f)
    
    for mailbox in list(set([mailbox for name, mailboxes in groups.items() for mailbox in mailboxes])) + ['998_Others']:
        for function in ['tmp', 'new', 'cur']:
            Path(os.path.join('/home/philcowans/Fedi', mailbox, function)).mkdir(parents=True, exist_ok=True)

    for fn in glob(f'{cache_base()}/*.json'):
        post = Post.from_file(fn)
        for mailbox in groups.get(post.full_account_name(), ['998_Others']):
            with open(f'/home/philcowans/Fedi/{mailbox}/new/{post.id()}', 'w') as f_mail:
                f_mail.write(f'Message-ID: <{post.id()}.philcowans@universeodon.com>\n')
                if post.in_reply_to_id() is not None:
                    f_mail.write(f'In-Reply-To: <{post.in_reply_to_id()}.philcowans@universeodon.com>\n')
                    f_mail.write(f'References: <{post.in_reply_to_id()}.philcowans@universeodon.com>\n')
                f_mail.write('To: Pippa <philcowans@universeodon.com>\n')
                date = datetime.fromisoformat(post.created_at()).strftime('%a, %d %b %Y %H:%M:%S %z')
                f_mail.write(f'Date: {date}\n')
                f_mail.write(f'From: {post.display_name()} <{post.full_account_name()}>\n')
                if post.reblog_content():
                    subject = f'Boost: {BeautifulSoup(post.reblog_content(), features='lxml').get_text()[:80]}' 
                else:
                    subject = f'{BeautifulSoup(post.content(), features='lxml').get_text()[:80]}' 
                f_mail.write(f'Subject: {subject}\n')
                f_mail.write('\n')
                if post.reblog_content():
                    content = f'Boost from {post.reblog_display_name()} <{post.reblog_full_account_name()}>\n'
                    content += '\n'
                    content += textwrap.fill(BeautifulSoup(post.reblog_content(), features='lxml').get_text(), 80)
                else:
                    content = textwrap.fill(BeautifulSoup(post.content(), features='lxml').get_text(), 80)
                f_mail.write(content)
                f_mail.write('\n')
                f_mail.write('\n')
                f_mail.write(f'Original URL: {post.url()}\n')
    

def _post_statuses(token, server):
    print('Posting queued statuses ... ', flush=True, end='')
    failed = False
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
        
        if response.status_code == 200:
            os.rename(f'{outbox_base()}/{file}', f'{sent_base()}/{file}')
        else:
            failed = True
    if failed:
        print('failed.')
    else:
        print('done.')

def _do_status_run():
    with open(state_filename(), encoding='utf-8') as f:
        state = json.load(f)
    print('Authenticating ... ', flush=True, end='')
    config = Config(os.environ['HOME'] + '/.config/fcli/config.ini')
    server = config.mastodon_server()
    username = config.mastodon_username()
    token = Auth.get_token(state, server, config)
    user_id = accounts_lookup(username, server=server, token=token)['id']
    print('done.')
    _post_statuses(token, server)

def _do_sync():
    with open(state_filename(), encoding='utf-8') as f:
        state = json.load(f)
    print('Authenticating ... ', flush=True, end='')
    config = Config(os.environ['HOME'] + '/.config/fcli/config.ini')
    server = config.mastodon_server()
    username = config.mastodon_username()
    token = Auth.get_token(state, server, config)
    user_id = accounts_lookup(username, server=server, token=token)['id']
    print('done.')
    print('Synchronising following list ... ', flush=True, end='')
    following = accounts_following(user_id, server=server, token=token)
    with open(following_filename(), 'w', encoding='utf-8') as f:
        json.dump(following, f)
    print('done.')
    _post_statuses(token, server)
    print('Fetching new posts ... ', flush=True, end='')

    max_id = state['max_id']

    num_fetched = 20 # pylint: disable=invalid-name

    pivot_by_username = defaultdict(list)

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
            account_key = response['account']['display_name'] + ' (' + response['account']['acct'] + ')'
            pivot_by_username[account_key].append(response_id)
            max_id = max([max_id, int(response_id)])
            with open(f'{cache_base()}/{response_id}.json', 'w', encoding='utf-8') as f:
                json.dump(response, f)

    print('done.')
    print('Writing post summary to file (/tmp/new_posts.txt) ... ', flush=True, end='')
    with open('/tmp/new_posts.txt', 'w') as new_posts_file:
        for acct, posts in pivot_by_username.items():
            new_posts_file.write(acct + ': ' + ','.join([str(post) for post in posts]) + '\n')
    print('done.')
    print('Fetching new notifications ... ', flush=True, end='')
    max_notification_id = state.get('max_notification_id', 0)
    notifications_response = notifications(max_notification_id, server, token)
    max_notification_id = max([int(notification['id']) for notification in notifications_response] + [max_notification_id])
    notification_counts = defaultdict(lambda : 0)
    for notification in notifications_response:
        notification_counts[notification['type']] += 1
        notification_id = notification['id']
        with open(f'/home/philcowans/Fedi/000_Notifications/new/{notification_id}', 'w') as f_mail:
            f_mail.write('To: Pippa <philcowans@universeodon.com>\n')
            date = datetime.fromisoformat(notification['created_at']).strftime('%a, %d %b %Y %H:%M:%S %z')
            f_mail.write(f'Date: {date}\n')
            notification_type = notification['type']
            #f_mail.write(f'From: {post.display_name()} <{post.full_account_name()}>\n')
            f_mail.write(f'Subject: Notification ({notification_type})\n')
            f_mail.write('\n')
            f_mail.write(json.dumps(notification, indent=2))
            f_mail.write('\n')
    print('done.')

    with open(state_filename(), 'w', encoding='utf-8') as f:
        json.dump({
            'max_id': max_id,
            'max_notification_id': max_notification_id,
            'token': token,
        }, f)

    print('Completed sync.')
    print('')
    print('Notificaiton summary: ' + ', '.join([f'{k} ({v})' for k, v in notification_counts.items()]))
    print('')
    input('Press enter to start review')

    return token

def _do_actions():
    print('Sending actions to Everdo ... ', flush=True, end='')
    files = list(os.listdir(f'{processed_base()}/actionable'))
    try:
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
                verify=False, #'./cert.pem',
                timeout=60
            )
            os.rename(f'{processed_base()}/actionable/{file}', f'{processed_base()}/actioned/{file}')
        print('done.')
    except requests.exceptions.ConnectionError:
        print('failed - connection refused, please retry later.')

if (len(sys.argv) == 1) or (sys.argv[1] == 'review'):
    print('')
    print('W\033[1melcome to fcli 1.0.1 - (c) 2023-2024 Phil Cowans\033[0m')
    print('')
    print('Released under the MIT license, see LICENSE for details')
    print('More info at https://github.com/philcowans/fcli')
    print('')
    print('Updating stats ... ', flush=True, end='')
    Ratings().account_summary().write_lists()
    print('done.')
    token = _do_sync()
    post_list = PostList()
    post_list.plan()
    files = post_list.get_filenames()

    start_time = time()
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
            for idx, url in enumerate(post.content_links()):
                print(f'{idx}: {url}')
            print('')
        if len(post.media_links()) > 0:
            print('## Attachments')
            for idx, url in enumerate(post.media_links()):
                print(f'{idx}: {url}')
            print('')
        finished = False # pylint: disable=invalid-name
        while not finished:
            action = input(
                'Action? (A)ctionable / (B)oost / (I)nteresting / (N)ot interesting / '
                '(U)nsure / (S)ource / (O)pen '
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
                link_type = input('Link type? (O)riginal / (L)ink / (A)ttachment ')
                if link_type == 'o':
                    subprocess.run(['open', post.url()], check=False)
                else:
                    try:
                        link_index = int(input('Link number? (Zero indexed) '))
                        try:
                            if link_type == 'l':
                                url = post.content_links()[link_index]
                                subprocess.run(['open', url], check=False)
                            elif link_type == 'a':
                                url = post.media_links()[link_index]
                                subprocess.run(['open', url], check=False)
                        except IndexError:
                            pass
                    except ValueError:
                        pass
    end_time = time()

    print('Pushing scheduled boosts ... ', flush=True, end='')
    config = Config(os.environ['HOME'] + '/.config/fcli/config.ini')
    server = config.mastodon_server()
    files = list(os.listdir(f'{processed_base()}/boostable'))
    for file in files:
        post = Post.from_file(f'{processed_base()}/boostable/{file}')
        response = requests.post(
            f'https://{server}/api/v1/statuses/{post.id()}/reblog',
            headers={
                'Authorization': f'Bearer {token}',
            },
            timeout=60
        )
        os.rename(f'{processed_base()}/boostable/{file}', f'{processed_base()}/boosted/{file}')
    print('done.')
    _do_actions()
    files = list(os.listdir(f'{cache_base()}'))
    for file in files:
        os.rename(f'{cache_base()}/{file}', f'{processed_base()}/skipped/{file}')
    print(f'Session time {end_time - start_time}')

elif sys.argv[1] == 'sync':
    _do_sync()

elif sys.argv[1] == 'post':
    _do_status_run()

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

elif sys.argv[1] == 'index':
    _do_index()

elif sys.argv[1] == 'sendmail':
    parser = BytesParser(policy=default)
    message = parser.parse(sys.stdin.buffer)
    if irt := message.get('In-Reply-To'):
        id_re = re.compile(r'<([0-9]*)\.')
        irt_id = id_re.match(irt)[1]
    else:
        irt_id = None
    with open(state_filename(), encoding='utf-8') as f:
        state = json.load(f)
    print('Authenticating ... ', flush=True, end='')
    config = Config(os.environ['HOME'] + '/.config/fcli/config.ini')
    server = config.mastodon_server()
    username = config.mastodon_username()
    token = Auth.get_token(state, server, config)
    user_id = accounts_lookup(username, server=server, token=token)['id']
    print('done.')
    print('Posting status ... ', flush=True, end='')
    failed = False
    form_data = {
        'status': message.get_content(),
        'visibility': 'public',
        'language': 'en',
        'in_reply_to_id': irt_id
    }

    response = requests.post(
        f'https://{server}/api/v1/statuses',
        headers={
            'Authorization': f'Bearer {token}',
        },
        data=form_data,
        timeout=60
    )
    
    if response.status_code != 200:
        failed = True
    if failed:
        print('failed.')
    else:
        print('done.')

elif sys.argv[1] == 'boost':
    parser = BytesParser(policy=default)
    message = parser.parse(sys.stdin.buffer)
    id_re = re.compile(r'<([0-9]*)\.')
    message_id = id_re.match(message.get('Message-ID'))[1]
    with open(state_filename(), encoding='utf-8') as f:
        state = json.load(f)
    print('Authenticating ... ', flush=True, end='')
    config = Config(os.environ['HOME'] + '/.config/fcli/config.ini')
    server = config.mastodon_server()
    username = config.mastodon_username()
    token = Auth.get_token(state, server, config)
    print('done.')
    response = requests.post(
        f'https://{server}/api/v1/statuses/{message_id}/reblog',
        headers={
            'Authorization': f'Bearer {token}',
        },
        timeout=60
    )
