'''Functionality to do with maintaining application state'''
import os

def _state_base():
    return os.environ['HOME'] + '/.fcli'

def state_filename():
    '''Filename to use for application state file'''
    return _state_base() + '/state.json'

def cache_base():
    '''Base directory for cache'''
    return _state_base() + '/cache'

def staging_base():
    '''Base directory for staging'''
    return _state_base() + '/staging'

def processed_base():
    '''Base directory for processed files'''
    return _state_base() + '/processed'

def lqa_filename():
    '''Filename for list of low quality accounts'''
    return _state_base() + '/low_quality_accounts.txt'

def hqa_filename():
    '''Filename for list of high quality accounts'''
    return _state_base() + '/high_quality_accounts.txt'
