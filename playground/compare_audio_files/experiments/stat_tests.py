import os

from scipy import stats
import numpy as np
import pandas as pd

DIR = 'experiment_results'

if __name__ == '__main__':
    _, _, filenames = next(os.walk(DIR))

    for filename in filenames:
        df = pd.read_csv(f'{DIR}/{filename}', index_col=0)
        df = df.mask(df.apply(lambda x: x.name == x.index))
        df.index = df.index.map(lambda x: x[0])
        df.columns = [c[0] for c in df.columns]

        df_same = df.mask(df.apply(lambda x: x.name != x.index))
        sample_same = df_same.values.flatten()
        sample_same = sample_same[~np.isnan(sample_same)]

        df_diff = df.mask(df.apply(lambda x: x.name == x.index))
        sample_diff = df_diff.values.flatten()
        sample_diff = sample_diff[~np.isnan(sample_diff)]

        # Welch's t-test
        # H0: mean(sample_same) == mean(sample_diff)
        confidence_level = 0.95
        pvalue = stats.ttest_ind(sample_same, sample_diff, equal_var=False).pvalue
        print(f'{filename}:')
        print(sample_same.mean(), sample_diff.mean())
        print(f'p-value: {pvalue} (means are {"not " if pvalue < 1 - confidence_level else ""}equal)\n')
