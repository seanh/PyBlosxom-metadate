#!/usr/bin/env python
"""rdate.py

Save the mtimes of your pyblosxom story files as metadata tags inside
the story files themselves.

The format of the tag is:

#published %Y-%m-%d %H:%M:%S

If rdate does not find a #published metadata tag inside a file it
inserts one using the mtime of the file.

If it does find a tag it checks to see if the mtime of the file matches
the time in the tag, and if not it restores the mtime of the file from
the tag.

A list of file or directory names should be given as command-line
argument.

The following options are available:

    -r : descend recursively into directories
    
    -v : verbose output
    
    -e .extension : filename extension to look for, including the .,
                    default is .txt
                    
    -d : do a dry-run, do not change the mtimes or contents of any files,
         but report on any that need to be changed.

    FIXME: currently if you pass a non-.txt filename as an argument you
           also have to give the -e extension, or rdate will ignore the
           file. This seems silly.

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished
to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Copyright 2007 David Zejda  (original version)
Copyright 2009 seanh (same idea, complete rewrite)

"""
__author__ = "seanh"
__version__ = "v 0.2 complete rewrite by seanh"
__url__ = "http://github.com/seanh/PyBlosxom-rdate/"
__description__ = "Remembers or restores the original mtime of an entry."

import os,datetime,time,sys,getopt

FMT = "#published %Y-%m-%d %H:%M:%S\n"
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
        f = open(filename,"r")
        try:
            lines = f.readlines()
        finally:
            f.close()
    except IOError, e:
        print "Failed to read file ",filename,e
        return
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

def savemtime(filename):
    """Save the mtime of a file in a #published tag in the file, if no
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

def restoremtime(filename):
    """Set the mtime of the file to the time specified in the #published
    metadata in the file. If no such metadata exists, do nothing."""

    # Look for a #published tag in the metadata of the story, if one is
    # found set the mtime of the file to the time given in the tag.
    if verbose: print filename
    entry = parsefile(filename)
    filestats = os.stat(filename)
    atime,mtime = filestats[7:9]
    fmtime = datetime.datetime.fromtimestamp(mtime)
    fmtime = fmtime.strftime(FMT)
    if verbose: print "  mtime: ",fmtime.rstrip()
    for item in entry["metadata"]:
        if item.startswith("#published "):
            if verbose: print "  Trying to restore remembered mtime."
            ttuple = time.strptime(item,FMT)
            if verbose: print "  parsed tuple:", ttuple
            epoch = time.mktime(ttuple)
            if verbose: print "  epoch seconds:", epoch
            if mtime != epoch:
                if dryrun:
                    print "mtime of", filename, "needs to be restored to", datetime.datetime.fromtimestamp(epoch).strftime(FMT).rstrip()
                else:
                    print "  Restoring mtime of ",filename," to ",datetime.datetime.fromtimestamp(epoch).strftime(FMT).rstrip()
                    os.utime(filename,(atime,epoch))
            return
    if verbose: print "  This file had no stored mtime."

def handle_file(filename):
    """If the filename ends with .txt then backup the mtime of the file.
    """

    # FIXME - this is a terrible check for whether something might be
    # an entry file.  Need a better method.
    if filename.endswith(ext):
        restoremtime(filename)
        savemtime(filename)
    else:
        if verbose: print "skipping '%s' (not .txt)...." % filename

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
    print "Syntax: python rdate.py <-r> <-v> <-d> [file|dir] <file|dir...>"
    
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
