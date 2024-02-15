'''Support for post filtering algorithms'''
import dataclasses
import os
import shutil

import numpy as np

from .post import Post
from .state import cache_base, staging_base, hqa_filename

@dataclasses.dataclass
class Algorithm:
    '''An algorithm for filtering posts'''
    hqa_filename: str = None
    non_lqa_count: int = 30
    lqa_count: int = 20

def get_filenames_with_algorithm(algorithm, all_files):
    '''Return the list of JSON filenames for the posts using algorithm'''
    with open(algorithm.hqa_filename or hqa_filename(), encoding='utf-8') as f:
        hqas = [l.strip() for l in f]

    files = list(np.random.choice([
        file[0]
        for file in all_files
        if (file[1].username() not in ['benb', 'HamiltonsLive'])
        and (file[1].full_account_name() in hqas)
    ], size=algorithm.non_lqa_count, replace=False))

    files += list(np.random.choice([
        file[0]
        for file in all_files
        if (file[1].username() not in ['benb', 'HamiltonsLive'])
        and (file[1].full_account_name() not in hqas)
    ], size=algorithm.lqa_count, replace=False))

    return files

class PostList:
    '''A filtered list of Posts'''
    def __init__(self, staging_path=None):
        staging_path = staging_path or staging_base()
        self._files = list(os.listdir(staging_path))

    def plan(
        self,
        path=None,
        staging_path=None,
        algorithm=None,
        copy_to_staging=False
    ):
        '''Generate the list, unless there's already one, in which case do nothing'''
        path = path or cache_base()
        staging_path = staging_path or staging_base()
        algorithm = algorithm or Algorithm()

        if len(self._files) > 0:
            return

        all_files = [
            (file, Post.from_file(f'{path}/{file}'))
            for file in os.listdir(path)
        ]

        self._files = get_filenames_with_algorithm(algorithm, all_files)

        for filename in self._files:
            if copy_to_staging:
                shutil.copy(f'{path}/{filename}', f'{staging_path}/{filename}')
            else:
                shutil.move(f'{path}/{filename}', f'{staging_path}/{filename}')

    def get_filenames(self):
        '''Return the list of JSON filenames for the posts'''
        return self._files
