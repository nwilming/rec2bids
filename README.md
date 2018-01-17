# rec2bids
Convert a set of recordings into BIDS standard


Organizing data from experiments can be a mess if data collection 
involves many measurement sessions with repeated measurements of
the same subject etc. This tool helps to organize data according 
to the BIDS standard. Note that this tool will only help with file
conversion and naming. Metadata etc. will need to be provided by
the user. When dcm2niix is used for DICOM conversion this will go 
very far though.

The core assumption of this tool is that no two experiments are 
alike and the only one who knows how to organize the data are those
who collected the data. rec2bids provides a very lightweight 
way to generate filenames according to the BIDS standard and to
copy files around. But it requires user input to identify the 
relevant aspects for each file from the user. This makes this
tool very versatile.

The second assumption of this tool is that you want some form of
documentation of how each raw dataset is treated. This is why you, the
user, need to provide an explicit mapping of files to properties.
In most cases recorded data already has a specific file naming scheme,
making identification a one shot coding effort. However, exceptions
to the default naming scheme (e.g. because a measurement had to be 
aborted) will need to be explicitly handled by the user. This is 
what provides transparent documentation of what happened with the
raw data.

rec2bids works by listing all files within a directory. In the 
next step it calls a user provided function that returns a list 
of properties for this file (subject, session, task etc.). rec2bids
generates appropriate BIDS filenames from these properties and can
then copy the raw data to a target destination. During identification
a file can be split into several parts or metadata might be generated
for each file.

The following sequence of operations is carried out for all files:

 1. File identification: Call user defined function that returns 
    a list of dicts with all relevant attributes (subject, session, 
    run, modality...) for each file. The reason that a list of dicts 
    is returned is, that sometimes it is necessary to split a single
    input file into several output files (e.g. physio recorded 
    across runs that needs to be split).
    Before file identification rec2bids can identify directories that
    contain only dicom images and convert these to NIFTI images with
    corresponding json sidecars (via dcm2niix).
 2. Order files that belong to the same subject, session, run and 
    modality in time. Ordering is done according to acquisition time
    which is acquired by a user defined function for each file.
 3. Generate BIDS compatible filenames.
 4. Move files to target directory.


A typical use case is:

   >>> from rec2bids import tobids, identify
   >>> r = tobids.BIDSTemplate(path)
   >>> r.process(identify.identify_file, identify.get_acquition_time, target_path)


The recommended way to use rec2bids is to pair it with a metadata 
script for each experiment that is converted. This script should:

 1. Identify all files.
 2. Convert behavioral logs to the correct tsv standard.
 3. Potentially split physio recordings into runs and convert to
    tsv.gz format.
 4. Generate json sidecars for each imaging file (dcm2niix will do
    this automatically during conversion).

