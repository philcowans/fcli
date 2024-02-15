'''Tests for post_list.py'''
import os
import shutil

from fcli.post_list import Algorithm, PostList

def test_file_list_generation():
    '''Test that PostList can generate filename lists'''
    try:
        shutil.rmtree('/tmp/fcli/staging')
    except FileNotFoundError:
        pass
    os.makedirs('/tmp/fcli/staging')
    subject = PostList(staging_path='/tmp/fcli/staging')
    algorithm = Algorithm(
        hqa_filename=os.path.dirname(os.path.realpath(__file__)) + '/fixtures/high_quality_accounts.txt',
        non_lqa_count=2,
        lqa_count=1
    )
    subject.plan(
        path=os.path.dirname(os.path.realpath(__file__)) + '/fixtures/cache',
        staging_path='/tmp/fcli/staging',
        algorithm=algorithm,
        copy_to_staging=True
    )
    filenames = subject.get_filenames()
    shutil.rmtree('/tmp/fcli/staging')
    assert len(filenames) == 3

def test_caching():
    '''Test that filenmane lists are persisted and recoovered if processing'''
    try:
        shutil.rmtree('/tmp/fcli/staging')
    except FileNotFoundError:
        pass
    os.makedirs('/tmp/fcli/staging')
    subject = PostList(staging_path='/tmp/fcli/staging')
    algorithm = Algorithm(
        hqa_filename=os.path.dirname(os.path.realpath(__file__)) + '/fixtures/high_quality_accounts.txt',
        non_lqa_count=2,
        lqa_count=1
    )
    subject.plan(
        path=os.path.dirname(os.path.realpath(__file__)) + '/fixtures/cache',
        staging_path='/tmp/fcli/staging',
        algorithm=algorithm,
        copy_to_staging=True
    )
    assert len(os.listdir('/tmp/fcli/staging')) == 3
    subject2 = PostList(staging_path='/tmp/fcli/staging')
    filenames = subject2.get_filenames()
    assert len(filenames) == 3
    shutil.rmtree('/tmp/fcli/staging')
