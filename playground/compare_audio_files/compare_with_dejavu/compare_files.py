import sys
import itertools
from collections import defaultdict, Counter
import numpy as np

from dejavu import Dejavu
import psycopg2
from contextlib import closing

from typing import List, Dict, Tuple

config = {
    'database': {
        'host': 'db',
        'user': 'postgres',
        'password': 'password',
        'dbname': 'dejavu'
    },
    'database_type': 'postgres'
}


class Recording:
    def __init__(self, filename: str):
        self.filename = filename
        self.fingerprints: List[Tuple[object, int]] = []
        self.agg_fingerprints: Dict[object, List[int]] = defaultdict(list)

    def aggregate_fingerprints(self):
        '''Aggregate offsets by hash.'''
        for fingerprint, offset in self.fingerprints:
            self.agg_fingerprints[fingerprint].append(offset)

    def get_fingerprints(self, aggregate=False):
        '''Get (hash, offset) pairs for the recording from the database.'''
        with closing(psycopg2.connect(**config['database'])) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f'SELECT f.hash, f.offset\
                                 FROM fingerprints f\
                                 LEFT JOIN songs s ON f.song_id = s.song_id\
                                 WHERE s.song_name = \'{self.filename}\';')
                self.fingerprints = sorted(cursor.fetchall(), key=lambda x: x[1])

        if aggregate:
            self.aggregate_fingerprints()

    def align(self, other) -> int:
        '''
        Determine the offset between two recordings.
        Find all common hashes in two recordings, calculate the differences between
        their offsets and take the most common offset.
        '''
        common: Dict[object, Tuple[List[int], List[int]]] = {}
        for fingerprint1, offsets1 in self.agg_fingerprints.items():
            if fingerprint1 in other.agg_fingerprints.keys():
                common[fingerprint1] = (offsets1, other.agg_fingerprints[fingerprint1])

        diff = []
        for fingerprint, offsets in common.items():
            diff.extend([f2 - f1 for f1, f2 in itertools.product(offsets[0], offsets[1])])

        most_common_diffs = Counter(diff).most_common(2)
        if most_common_diffs[0][1] < most_common_diffs[1][1] * 10:
            offset = 0
        else:
            offset = most_common_diffs[0][0]

        return offset

    def compare(self, other) -> bool:
        '''
        Count the similarity metric between two recordings and decide if they are similar or not.
        '''
        global_offset = self.align(other)

        if global_offset < 0:
            self, other = other, self
            global_offset = abs(global_offset)

        common_length = min(len(self.fingerprints), len(other.fingerprints))

        combined_fingerprints = [([], []) for _ in range(common_length)]
        for fingerprint, offset in self.fingerprints:
            if offset + global_offset < common_length:
                combined_fingerprints[offset + global_offset][0].append(fingerprint)
        for fingerprint, offset in other.fingerprints:
            if offset < common_length:
                combined_fingerprints[offset][1].append(fingerprint)

        common_proportion = []
        for fingerprints1, fingerprints2 in combined_fingerprints:
            common = [f1 == f2 for f1, f2 in itertools.product(fingerprints1, fingerprints2)]
            common_proportion.append(sum(common) / (len(fingerprints1) + len(fingerprints2) + 1))

        similarity = np.mean(common_proportion)

        return similarity


if __name__ == '__main__':
    filename1, filename2 = sys.argv[1:]

    extension = filename1.split('.')[-1]

    file1, file2 = list(map(lambda s: s.split('/')[-1][:-(len(extension) + 1)], [filename1, filename2]))

    djv = Dejavu(config)

    #djv.fingerprint_directory('data', [extension])

    djv.fingerprint_file(f'./data/{file1}.{extension}')
    djv.fingerprint_file(f'./data/{file2}.{extension}')

    rec1, rec2 = Recording(file1), Recording(file2)

    rec1.get_fingerprints(aggregate=True)
    rec2.get_fingerprints(aggregate=True)

    similarity = rec1.compare(rec2)
