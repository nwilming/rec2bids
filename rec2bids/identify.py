'''
Provide meta data for recording data.
'''

import os
import re
import time
import tobids

from joblib import Memory
from pyedfread import edfread
from scipy.io import loadmat
from scipy.io.matlab.miobase import MatReadError

memory = Memory(cachedir='/Users/nwilming/u/flexible_rule/cache', verbose=0)


def identify_file(filename):
    '''
    Identifies a file to make it BIDS compatible.

    Input is the absolute path of the file to be identified.

    Output:
        dict with fields:
            file = str
                Absolute path of this file. This can potentially
                be different from the input path, thereby allowing
                for file conversions / splitting etc.
            subject = str or int.
                Subject identifier. Tobids will prefix 'sub-' to this.
            session = str or int.
                Session identifier. Tobids will prefix 'ses-' to this.
            run = str or int or None
                Run identifier. Tobids will prefix 'run-' to this.
            data_type = str
                Type of data (anat/func/beh/dwi)
            task = str or None
                Task identifier. Tobids will prefix 'task-' to this.
            acq = str or None
                This is a user defined label that can be used to distinguish
                recordings that only differe in some parameter that is not
                captured by all other labels. For example if two T1w images
                were captured and one is high res and the other low res.
            file_format = str
                File format (e.g. 'nii', 'edf' etc.)
            modality =  str
                Recording modality. E.g. 'bold' for fMRI, 'T1w' for
                anatomical T1 image.
    '''

    results = ident_behav(filename)
    if results is None:
        raise tobids.Skip(filename)
    return results


def ident_behav(filename):
    '''
    Identify a file from the immuno experiment.
    '''
    task_map = {1: dict((i, 'inference') for i in range(1, 8)),
                2: dict((i, 'predict') for i in range(1, 8)),
                3: dict((i, 'inference') for i in range(1, 8)),
                4: dict((i, 'predict') for i in range(1, 8)),
                5: dict((i, 'inference') for i in range(1, 8)),
                6: dict((i, 'predict') for i in range(1, 8))}
    p = re.compile('S\d+_P\d_B\d')
    if (p.search(filename) and
            (filename.lower().endswith('mat')
                or filename.lower().endswith('edf'))):
        ftype_mapping = {'mat': 'func', 'edf': 'func'}

        fileend = filename.split('/')[-1]
        parts = fileend.split('_')
        subject = int(parts[0][1:])
        session = int(parts[1][1:])
        block = int(parts[2][1:])
        file_format = parts[-1].split('.')[-1]
        data_type = ftype_mapping[file_format]
        return {'file': filename,
                'subject': '%02i' % subject,
                'session': '%02i' % session,
                'run': '%02i' % block,
                'data_type': data_type,
                'task': task_map[session][block],
                'file_format': file_format,
                'modality': {'mat': 'stim', 'edf': 'physio'}[file_format]}


def parse(string, tokens):
    '''
    Extract all numbers following token.
    '''
    numbers = dict((t, [int(n.replace(t, ''))
                        for n in re.findall(t + '\d+', string)])
                   for t in tokens)
    return numbers


@memory.cache
def get_mat_p(filename):
    return loadmat(filename)['p']['start_time'][0, 0][0]


@memory.cache
def get_edf_p(filename):
    return edfread.read_preamble(filename).decode(
        'utf-8').split('\n')[0]


def get_acquisition_time(filename):
    fformat = filename.split('.')[-1]
    if fformat == 'mat':
        try:
            p = get_mat_p(filename)
            try:
                return time.strptime(p, '%d-%b-%y-%H:%M:%S')
            except ValueError:
                return time.strptime(p, '%d-%b-%y-%H%M%S')
        except (OSError, MatReadError):
            print('Could not read %s' % filename)

    if fformat == 'edf':
        try:
            t = get_edf_p(filename)
            assert('DATE' in t)
            return time.strptime(t, '** DATE: %a %b %d  %H:%M:%S %Y')
        except OSError:
            print('Could not read %s' % filename)
    if fformat == 'smr':
        return time.ctime(os.path.getctime(filename))
