'''Tests for config.py'''
import os

from fcli.config import Config

def test_attributes():
    '''Test that configuration attributes are correctly extracted from the configuration file'''
    subject = Config(path=os.path.dirname(os.path.realpath(__file__)) + '/fixtures/config.ini')
    assert subject.mastodon_server() == 'Test Mastodon Server'
    assert subject.mastodon_client_id() == 'Test Mastodon Client ID'
    assert subject.mastodon_client_secret() == 'Test Mastodon Client Secret'
    assert subject.everdo_key() == 'Test Everdo Key'
