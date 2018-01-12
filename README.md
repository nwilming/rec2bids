# rec2bids
Convert a set of recordings into BIDS standard


Organizing data from experiments can be a mess if data collection 
involves many measurement sessions with repeated measurements of
the same subject etc. This tool helps to organize data according 
to the BIDS standard. 

The core assumption of this tool is that no two experiments are 
alike and the only one who knows how to organize the data are those
who collected the data. rec2bids provides a very lightweight 
way to generate filenames according to the BIDS standard and to
copy files around. But it requires user input to identify the 
relevant aspects for each file from the user. This makes this
tool very versatile.

The second assumption if this tool is that you want some form of
documentation of how each raw dataset is treated. This is why the
user needs to provide an explicit mapping of files to properties.
In most cases recorded data already has a specific file naming scheme,
making identification a one shot coding effort. However, exceptions
to the default naming scheme (e.g. because a measurement had to be 
aborted) will need to be explicitly handled by the user. This is 
what provides transparent documentation of what happened with the
raw data.

rec2bids works by identifying all files within a directory. In the 
next step it calls a user provided function that returns a list 
of properties for this file (subject, session, task etc.). rec2bids
generates appropriate BIDS filenames from these properties and can
then copy the raw data to an appropriate place. During identification
a file can be split into several parts or metadata might be generated
for each file.

A typical use case is:

   >>> from rec2bids import tobids, identify
   >>> r = tobids.BIDSTemplate(path)
   >>> r.process(identify.identify_file, identify.get_acquition_time, target_path)

