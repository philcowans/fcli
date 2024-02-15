'''Tests for post.py'''
import json
import os

from fcli.post import Post

def test_attributes():
    '''Test that attributes are returned as expected'''
    with open(os.path.dirname(os.path.realpath(__file__)) + '/fixtures/test_post.json', encoding='utf-8') as f:
        test_post = json.load(f)
    subject = Post(test_post)
    assert subject.display_name() == 'Howard Rheingold'
    assert subject.full_account_name() == 'hrheingold@mastodon.social'
    assert subject.username() == 'hrheingold'
    assert subject.url() == 'https://mstdn.ca/@jocelyn/111353289971446465'
    assert subject.content() == ''
    assert len(subject.reblog_content()) == 1069
    assert subject.media_links() == []

def test_content_links():
    '''Test that content links are returned as expected'''
    with open(os.path.dirname(os.path.realpath(__file__)) + '/fixtures/test_post.json', encoding='utf-8') as f:
        test_post = json.load(f)
    subject = Post(test_post)
    assert subject.content_links() == [
        'https://mamot.fr/@doctorow',
        'https://mamot.fr/@pluralistic',
        'https://mstdn.ca/tags/Enshittification',
        'https://youtu.be/rimtaSgGz_4?si=-mq3KmQbihVKYc-r'
    ]

def test_media_links():
    '''Test that media links are returned as expected'''
    with open(os.path.dirname(os.path.realpath(__file__)) + '/fixtures/test_post_with_media_attachments.json', encoding='utf-8') as f:
        subject = Post(json.load(f))
    assert len(subject.media_links()) == 1

def test_from_file():
    '''Test that Post can be deserialised from file'''
    subject = Post.from_file(os.path.dirname(os.path.realpath(__file__)) + '/fixtures/test_post.json')
    assert subject.display_name() == 'Howard Rheingold'
