'''Classes to support account level analytics.'''

import json
import os
import pandas as pd

from scipy.stats import beta

from .state import cache_base, processed_base, lqa_filename, hqa_filename

class Ratings:
    ''' Structured data about post ratings. '''
    def to_df(self):
        ''' Convert to a Pandas DataFrame. '''
        posts = []
        for status in ['unprocessed', 'actionable', 'actioned', 'interesting', 'not_interesting']:
            if status == 'unprocessed':
                path = cache_base()
            else:
                path = processed_base() + '/' + status
            for file in os.listdir(path):
                with open(f'{path}/{file}', encoding='utf-8') as f:
                    post = json.load(f)
                rb = (post['reblog'] and post['reblog']['account']['acct']) or ''
                posts.append({
                    'Date': post['created_at'][:10],
                    'Account': post['account']['acct'],
                    'Status': status,
                    'Reblog': rb,
                })
        return pd.DataFrame(posts)

    def account_summary(self):
        ''' Return an AccountSummary object covering the post ratings. '''
        return AccountSummary(self.to_df())

class AccountSummary:
    ''' Structured data about accounts.'''
    def __init__(self, all_posts):
        self._all_posts = all_posts

    def to_df(self):
        ''' Convert to a Pandas DataFrame. '''
        interesting_posts = self._all_posts[
            (self._all_posts['Status'] == 'interesting')
            | (self._all_posts['Status'] == 'actionable')
            | (self._all_posts['Status'] == 'actioned')
        ]
        seen_posts = self._all_posts[self._all_posts['Status'] != 'unprocessed']
        summary = (
            seen_posts.groupby('Account')
                .agg(seen_post_count=('Date', 'count'))
                .reset_index()
                .merge(
                    interesting_posts.groupby('Account')
                        .agg(interesting_post_count=('Date', 'count'))
                        .reset_index(),
                    how='left'
                )
                .fillna(0)
            )
        summary['interesting_post_ratio'] = (
                summary['interesting_post_count'] / summary['seen_post_count']
        )
        mu = summary['interesting_post_ratio'].mean()
        sigma = summary['interesting_post_ratio'].std()
        #print(f'Interesting post stats: mean = {mu}, st.dev. = {sigma}')
        a = (mu*mu)*(1-mu)/(sigma*sigma)-mu
        b = (a/mu)*(1-mu)
        #print(f'Moment matching parameters: alpha = {a}, beta = {b}')
        summary['p_low_quality'] = summary.apply(
            lambda x: beta.cdf(
                0.25,
                a + x['interesting_post_count'],
                b + x['seen_post_count'] - x['interesting_post_count']
            ),
            axis=1
        )
        summary['discard'] = summary['p_low_quality'].apply(lambda x: 1 if x > 0.5 else 0)
        return summary

    def write_lists(self):
        ''' Write low and high quality account lists to file. '''
        summary = self.to_df()
        with open(lqa_filename(), 'w', encoding='utf-8') as f:
            for account in summary[summary['discard'] == 1]['Account']:
                f.write(account + '\n')
        with open(hqa_filename(), 'w', encoding='utf-8') as f:
            for account in summary[summary['discard'] == 0]['Account']:
                f.write(account + '\n')
