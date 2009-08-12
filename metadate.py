#!/usr/bin/env python
"""metadate.py pyblosxom plugin.

If an entry contains a suitable #published metadata value then use this value as
the entry's date instead of the file's mtime. The required format of the
metadata line is #published %Y-%m-%d %H:%M:%S.

Example of an entry with a #published metadata value:

    This is the title of my entry
    #published 2009-08-05 22:36:17

    This is the content of my entry.

This plugin can also be run as a command-line utility to add #published values
to entry files that don't already have them, based on their mtimes. A list of
file or directory names should be given as the command-line argument. See
`./metadata.py --help` for command-line options.

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation, Inc., 59 Temple
Place, Suite 330, Boston, MA 02111-1307 USA

Copyright 2009 seanh, based on the idea from David Zejda's rdate plugin.

"""
#FIXME: currently if you pass a non-.txt filename as an argument you also have
# to give the -e extension, or metadate will ignore the file. This seems silly.

__author__ = 'Sean Hammond'
__homepage__ = 'http://github.com/seanh/PyBlosxom-metadate'
__email__ = 'seanh.nospam@gmail.com'
__version__ = "1"
__description__ = "Read entry dates from pyblosxom metadata values instead of file mtimes."

import os,re,datetime,time,sys,getopt

# The regex used to extract #published lines from files.
TIMESTAMP = re.compile('#published (?P<year>[0-9]{4})-(?P<month>[0-1][0-9])-(?P<day>[0-3][0-9]) (?P<hour>[0-2][0-9]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])')

# The strftime format used when writing new #published lines to files.
FMT = "#published %Y-%m-%d %H:%M:%S\n"

# The command-line options and their default values.
ext = '.txt'
verbose = False
dryrun = False

def parsefile(filename):
    """Read in the contents of a pyblosxom story file, and parse them.
        
    filename: the file to read
    
    return : a dictionary in which the keys 'title', 'metadata' and
             'body' correspond to the respective parts of the pyblosxom
             story.
    
    """
    try:
        f = open(filename,'r')
        try:
            lines = f.readlines()
        finally:
            f.close()
    except IOError, e:
        raise e
    mode = 0
    title = ""
    metadata = []
    body = []
    for item in lines:
        if mode == 0:
            title = item
            mode = 1
        elif mode == 1 and item.startswith("#"):
            metadata.append( item )
        else:
            mode = 2
            body.append( item )
    return { "title": title, "metadata": metadata, "body": body }

# The PyBlosxom plugin
# --------------------

def cb_filestat(args):
    """Parse the entry file looking for a #published metadata value. If the
    entry has a suitable value then override the mtime.
    
    """
    from Pyblosxom import tools
    # Parse the entry file.
    # Does a plugin really have to parse the entry file itself, it can't get a
    # parsed object from pyblosxom?
    filename = args['filename']
    datadir = args['request'].getConfiguration()['datadir']
    logger = tools.getLogger()
    try:
        entry = parsefile(os.path.join(datadir,filename))
    except IOError, e:
        logger.error(e)
        return args
    
    # If we find a #published metadata line in the entry load it into the args
    # dict and return. If not just return args unmodified.    
    stattuple = args['mtime']
    for metaline in entry['metadata']:
        match = TIMESTAMP.match(metaline)
        if match is not None:
            year = int(match.group('year'))
            month = int(match.group('month'))
            day = int(match.group('day'))
            hour = int(match.group('hour'))
            minute = int(match.group('minute'))
            second = int(match.group('second'))
            # This gets ugly, we have to somehow convert of year, month, day,
            # hour, minute and second numbers into an epoch time and then load
            # it into the tuple from os.stat. These next two lines are taken
            # from Tim Roberts' pyfilenametime plugin, I don't understand them.
            mtime = time.mktime((year,month,day,hour,minute,second,0,0,-1))
            args['mtime'] = tuple(list(stattuple[:8]) + [mtime] + list(stattuple[9:]))
    return args

# The command-line stuff
# ----------------------

def savemtime(filename):
    """Save the mtime of a file in a #published tag in the file if no
       such tag already exists, otherwise do nothing."""
    
    # Get the current mtime of the file from the system.
    if verbose: print "Targetted file:", filename
    filestats = os.stat(filename)
    atime,mtime = filestats[7:9]
    fmtime = datetime.datetime.fromtimestamp(mtime)
    fmtime = fmtime.strftime(FMT)
    if verbose: print "  current mtime:", fmtime.rstrip()

    # Check that the file doesn't already have a #published tag.
    entry = parsefile(filename)
    for item in entry["metadata"]:
        if item.startswith("#published "):
            # this item already has a published line, so we
            # exit.
            return

    if dryrun:
        print fmtime.rstrip(), "needs to be added to", filename
        return
        
    # Add a #published tag to the file, then set the access and modified
    # times of the file back to what they were.
    # FIXME: No exception handling here?
    print "  Adding ", fmtime.rstrip(), "to ", filename
    entry["metadata"].insert(0, fmtime)
    f = open(filename, "w")
    f.write( entry["title"] )
    f.write( "".join(entry["metadata"]) )
    f.write( "".join(entry["body"]) )
    f.close()
    os.utime(filename,(atime, mtime))

def handle_file(filename):
    """If the filename ends with `ext` then backup the mtime of the file.
    """

    if filename.endswith(ext):
        savemtime(filename)
    else:
        if verbose: print "skipping '"+filename+"' (not "+ext+")...."

def handle_directory(d,recursive):
    """Backup the mtimes of all the pyblosxom stories in the given
    directory, recursing into subdirectories if specified."""
    for mem in os.listdir(d):
        fn = os.path.join(d,mem)
        if os.path.isfile(fn):
            handle_file(fn)
        elif os.path.isdir(fn) and recursive:
            handle_directory(fn,recursive)
    
def usage():
    print "Syntax: python metadate.py <-r> <-v> <-d> <-e=EXTENSION> [file|dir] <file|dir...>"
    print """
The following options are available:

    -r : descend recursively into directories
    
    -v : verbose output
                        
    -d : do a dry-run, do not change the mtimes or contents of any files,
         but report on any that need to be changed.

    -e .extension : filename extension to look for, including the .,
                    default is .txt
"""
    
if __name__ == "__main__":
    try:
        opts,args = getopt.getopt(sys.argv[1:],"rvde:",["recursive","verbose","dry-run","extension="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    recursive = False
    if not args: usage()
    for option,value in opts:
        if option in ("-r","--recursive"):
            recursive = True
        if option in ("-v","--verbose"):
            verbose = True
        if option in ("-e","--extension"):
            ext = value
        if option in ("-d","--dry-run"):
            dryrun = True
    for argument in args:
        if not (os.path.isdir(argument) or os.path.isfile(argument)):
            usage()
            sys.exit(2)
    for argument in args:
        if os.path.isdir(argument):
            handle_directory(argument,recursive)
        elif os.path.isfile(argument):
            handle_file(argument)
