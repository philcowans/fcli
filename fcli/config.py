''' Classes associated with configuring fcli. '''

from configparser import ConfigParser

class Config:
    ''' fcli configuration data. This is stored in a .ini file.'''
    def __init__(self, path):
        self._config = ConfigParser()
        self._config.read(path)

    def everdo_key(self):
        ''' API key for the local Everdo API. '''
        return self._config['Everdo']['Key']

    def mastodon_server(self):
        ''' Mastodon server to connect to. '''
        return self._config['Mastodon']['Server']

    def mastodon_username(self):
        ''' Mastodon server to connect to. '''
        return self._config['Mastodon']['Username']

    def mastodon_client_id(self):
        ''' Mastodon client / application ID. '''
        return self._config['Mastodon']['ClientID']

    def mastodon_client_secret(self):
        ''' Mastodon client secret. '''
        return self._config['Mastodon']['ClientSecret']
