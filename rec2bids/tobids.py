'''
Convert an MR dataset to bids standard.
'''
from glob import glob
from os.path import join
import os
from os import makedirs
from subprocess import call, check_output
import json
import logging
from shutil import copy
import collections
from tqdm import tqdm

log = logging.getLogger(__name__)
log.setLevel(-10)

from joblib import Memory
memory = Memory(cachedir='/Users/nwilming/u/flexible_rule/cache', verbose=0)


class Skip(Exception):
    pass


class BIDSTemplate(object):
    '''
    Describes a data set and coresponding files in terms
    of subject, session and data type.

    Instantiating a BIDSTemplate finds all files in a direcotry
    and tries to identify these files by calling a user defined
    function with the filename of the to be identified file.
    This function should return a dictionary with the following keys:

    file : str
        The filename to add to the BIDS template. The user function can
        potentially return a different filenmae than is given to the
        function. This allows for format conversions etc.

    subject : participant label
        The BIDS-Template will prefix this with 'sub-' to conform to
        BIDS standard.

    session : session label
        The BIDS-Template will prefix this with 'ses-' to conform to
        BIDS standard.

    run : run index

    data_type : type of data (anat/func/beh/dwi)

    task : task label

    acq : acquisition labels
        This is a user defined label that can be used to distinguish
        recordings that only differe in some parameter that is not
        captured by all other labels. For example if two T1w images
        were captured and one is high res and the other low res.

    file_format : File format (e.g. 'nii', 'edf' etc.)

    modality : Recording modality
        E.g. 'bold' for fMRI, 'T1w' for anatomical T1 image.
    '''

    def __init__(self, path, session=True, convert_dicom=None):
        self.path = path
        self.files = list(walk(path))
        print('Found %i files in %s' % (len(self.files), path))

        if convert_dicom:
            ds = DicomSet(self.files, convert_dir=convert_dicom)
            self.files = ds.convert()
        depth = 5
        if session:
            depth = 6
        self.mapping = ddict(depth)
        self.multi_file = []

    def process(self, ident_func, sort_func, target):
        self.identify(ident_func)
        self.sort(sort_func)
        self.generate_filenames()
        self.move(target)

    def identify(self, func):
        '''
        Walk through all filenames and identify subject,
        session, run and data type.
        '''
        for file in self.files:
            try:

                files = func(file)
                if type(files) == dict:
                    self.add(**files)
                else:
                    for f in files:
                        self.add(**f)
            except Skip:
                continue
        return json.dumps(self.mapping, indent=2)

    def add(self, file=None, subject=None, session=None,
            run=None, data_type=None, task=None, acq=None,
            file_format=None, modality=None):
        if not subject.startswith('sub-'):
            subject = 'sub-' + subject
        if not session.startswith('sub-'):
            session = 'ses-' + session
        next_entry = {'source': file,
                      'params': {
                          'subject': subject,
                          'session': session,
                          'run': run,
                          'data_type': data_type,
                          'task': task,
                          'acq': acq,
                          'file_format': file_format,
                          'modality': modality}
                      }
        if len(self.mapping[subject][session][run][
               data_type][file_format]) > 0:
            # Duplicate Entry
            self.mapping[subject][session][run][
                data_type][file_format].append(next_entry)
        else:
            new_list = [next_entry]
            self.mapping[subject][session][run][
                data_type][file_format] = new_list
            self.multi_file.append(new_list)

    def sort(self, get_time):
        for mf in self.multi_file:
            if len(mf) > 1:
                mf.sort(key=lambda x: get_time(x['source']))

    def generate_filenames(self, order=False):
        for mf in self.multi_file:
            if len(mf) == 1:
                target_filename = self.to_bids_filename(**mf[0]['params'])
                mf[0]['target'] = target_filename
            else:
                ord = None
                for i, m in enumerate(mf):
                    if order:
                        ord = i + 1
                    params = m['params']
                    params['order'] = ord
                    target_filename = self.to_bids_filename(
                        **params)
                    m['target'] = target_filename

    def to_bids_filename(self, file=None, subject=None, session=None,
                         run=None, data_type=None, task=None, acq=None,
                         file_format=None, modality=None, order=None):
        '''
        Generate BIDS compatible filename
        '''
        if session is None:
            path = joinpath(subject, data_type)
            filename = subject
        else:
            path = joinpath(subject, session, data_type)
            filename = subject + '_' + session
        if task is not None:
            filename += '_task-' + task
        if acq is not None:
            filename += '_' + acq
        if run is not None:
            filename += '_run-' + str(run)
        if order is not None:
            filename += 'ORD%02i' % order
        filename += '_' + modality

        filename += '.' + file_format
        return joinpath(path, filename)

    def move(self, path):
        for mf in tqdm(self.multi_file):
            for m in mf:
                source = m['source']
                target = joinpath(path, m['target'])

                makedirs(os.path.dirname(target), exist_ok=True)
                copy(source, target)


class DicomSet(object):
    '''
    Convert DICOM to nifti before processing.
    '''

    def __init__(self, filenames, convert_dir=None,
                 check_dicom_dir=False):
        '''
        Initialize with a list of filenames.

        Find directories that only contain DICOM files and convert these
        directories with dcm2niix.

        '''
        from os.path import dirname
        self.original_filenames = set(filenames)
        self.datasets = set([dirname(f) for f in filenames])
        if check_dicom_dir is False:
            is_dicom_dir = lambda x: True if len(
                get_subdirectories(x)) == 0 else False
        self.datasets = set(
            [f for f in tqdm(self.datasets) if is_dicom_dir(f)])
        rm_files = [glob(join(d, '*')) for d in self.datasets]
        self.remaining_files = self.original_filenames.copy()
        for rm in rm_files:
            self.remaining_files -= set(rm)
        self.output_dir = convert_dir

    def convert(self):
        for dataset in tqdm(self.datasets):
            dicom_convert(dataset, self.output_dir)
        json = glob(join(self.output_dir, '*json'))
        nifti = glob(join(self.output_dir, '*.nii'))
        self.converted = json, nifti
        self.filelist = self.original_filenames.union(
            set(json)).union(set(nifti))
        return self.filelist


@memory.cache
def dicom_convert(dataset, output_dir):
    makedirs(output_dir, exist_ok=True)
    return call(["dcm2niix", "-9", "-b y", "-o", output_dir, dataset])


def is_dicom_dir(filename):
    ret = check_output(["file", *glob(join(filename, '*'))]).decode('utf-8')
    ret = ret.replace(filename, '')
    return all(['DICOM' in r for r in ret.splitlines()])


def joinpath(*args):
    return join(*[x for x in args if x is not None])


def walk(path):
    '''
    Generate all files in a dir (complete pathes).
    '''
    for p, _, fnames in os.walk(path):
        for ff in fnames:
            yield os.path.join(p, ff)


def get_subdirectories(a_dir):
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]


def ddict(n):
    if n == 0:
        x = lambda: {[]}
        return x
    else:
        return collections.defaultdict(lambda: ddict(n - 1))
