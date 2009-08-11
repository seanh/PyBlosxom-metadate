"""
If an entry contains a suitable #published metadata line then use this value as
the entry's date instead of the file's mtime. The required format of the
metadata line is #published %Y-%m-%d %H:%M:%S.

Example of an entry with a #published metadata line:

    This is the title of my entry
    #published 2009-08-05 22:36:17

    This is the content of my entry.

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

"""
__author__ = 'Sean Hammond'
__homepage__ = 'http://github.com/seanh/PyBlosxom-rdate'
__email__ = 'seanh.nospam@gmail.com'
__version__ = '1'
__description__ = "Use #published metadata lines as the dates of entries instead of file mtimes."
import os, re, time
from Pyblosxom import tools

TIMESTAMP = re.compile('#published (?P<year>[0-9]{4})-(?P<month>[0-1][0-9])-(?P<day>[0-3][0-9]) (?P<hour>[0-2][0-9]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])')

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

def cb_filestat(args):
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
