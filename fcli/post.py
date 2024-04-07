'''Functionality related to representing individual posts'''
import json
import textwrap

from bs4 import BeautifulSoup, SoupStrainer

class Post:
    '''An individual post'''
    def __init__(self, data):
        self._data = data

    @classmethod
    def from_file(cls, filename):
        '''Instantiate Post from JSON file'''
        with open(filename, encoding='utf-8') as f:
            return cls(json.load(f))

    def content(self):
        '''The content of the post'''
        return self._data['content']

    def display_name(self):
        '''The display name of the author'''
        return self._data['account']['display_name']

    def full_account_name(self):
        '''The full account name of the author'''
        return self._data['account']['acct']

    @staticmethod
    def _extract_links(html):
        return [
            link['href']
            for link in BeautifulSoup(
                html,
                parse_only=SoupStrainer('a'),
                features='lxml'
            )
            if link.has_attr('href')
        ]

    def content_links(self):
        '''URLs for all links present in the content'''
        links = self._extract_links(self._data['content'])
        if self._data['reblog']:
            links += self._extract_links(self._data['reblog']['content'])
        return links

    def media_links(self):
        '''URLs for all media links attached to the post'''
        media_attachments = self._data['media_attachments']
        if self._data['reblog']:
            media_attachments += self._data['reblog']['media_attachments']
        return [a['url'] for a in media_attachments]

    def reblog_content(self):
        '''Reblogged content, if present'''
        return (
            self._data['reblog']
            and self._data['reblog']['content']
        )

    def text_for_action(self):
        note = textwrap.fill(BeautifulSoup(self._data['content'], features='lxml').get_text(), 80) # pylint: disable=invalid-name
        media_attachments = self._data['media_attachments']
        if self._data['reblog']:
            note += '\n## Reblog\n'
            note += textwrap.fill(
                BeautifulSoup(self._data['reblog']['content'], features='lxml').get_text(), 80
            )
            media_attachments += self._data['reblog']['media_attachments']
        if len(media_attachments) > 0:
            note += '\n## Attachments\n'
            for a in media_attachments:
                note += a['url'] + '\n'
        note += '\n\nURL: ' + self.url() + '\n'
        return note

    def url(self):
        '''The URL for the post, or for the reblogged content'''
        return (
            (
                self._data['reblog']
                and self._data['reblog']['url']
            )
            or self._data['url']
        )

    def username(self):
        '''The username of the author'''
        return self._data['account']['username']

    def id(self):
        return self._data['id']
