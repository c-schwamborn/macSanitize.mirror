#!/usr/bin/env python3
# coding:utf-8
#
__author__ = "Christian Schwamborn <christian.schwamborn@nswit.de>"
__copyright__ = "Copyright 2024 Christian Schwamborn"
__license__ = "GPL v.3"

'''
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <https://www.gnu.org/licenses/>.
'''

import os
import sys
import re
import logging
from copy import deepcopy 
import configparser
import argparse
import textwrap
import pwd, grp

# TODO: implement parameters for:
# extension_length = 6

# reqular expressions
l_space = r'^(\s+).*$'
t_space = r'^.*[^\s](\s+)$'
uglies = r'(["|\\:*?<>]+)'
filename = r'^(.*[^.])\.(\s*\w{1,6})$'

# statistic counters
mod = False
ntotal = [0, 0, 0]
nren = [0, 0, 0]
nmod = [0, 0, 0]
nskip = [0, 0, 0]
nfail = [0, 0, 0]


def ownedFileHandler(filename, mode='a', encoding=None, owner=None):

	if owner:
		# convert user and group names to uid and gid
		uid = pwd.getpwnam(owner[0]).pw_uid
		gid = grp.getgrnam(owner[1]).gr_gid
		owner = (uid, gid)
		if not os.path.exists(filename):
			open(filename, 'a').close()
		os.chown(filename, *owner)

	return logging.FileHandler(filename, mode, encoding)


def getArgs():

	global args
	parser = argparse.ArgumentParser(
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description=textwrap.dedent('''\
			macSanitize will help you to remove characters from file or
			directory names that violates the smb standard and will
			therefore result in empty directories or being invisible when
			shared by samba.
			It can also remove leading/trailing spaces also causing files
			and directories not behaving as expected.
			Most common cause for those names, are file and directoy
			originating on Apple computers, as those systems allow anything
			ugly in file names.
			Unwanted characters are replaced by an underscore(_) and
			leading/trailing spaces are simply stripped.
			To avoid conflicts a number index is appended if the resulting
			file already exists in the current directory. The index is
			appended before the file extension. The file extension is
			detected by a dot(.) followed by 1 to 6 alphanumeric
			characters.
			'''),
		epilog=textwrap.dedent('''\
			Example:
				macSanitize.py -f -d -l -t -e -u /path/to/sanitize/

			Config example (default file: /etc/macSanitize.ini)

				[macSanitize]
				uglies = "|\\\:*?<>
				replacement = _
				folder skiplist = ,.AppleDouble
				file skiplist =

			Shown values are the defaults, the list delimiter is the first
			character found on the value side of the list parameter.
			Certain characters in uglies like a backslash(\\) or square
			brackets([]) must be escaped, as they are compiled into a
			regular expression.
			'''),
		)

	parser.add_argument(
		'-f', '--files',
		dest = 'process_files',
		action = 'store_true',
		required = False,
		default = False,
		help = 'process file objects at the given work directory',
		)

	parser.add_argument(
		'-d', '--directories',
		dest = 'process_dirs',
		action = 'store_true',
		required = False,
		default = False,
		help = 'process directory objects at the given work directory',
		)

	parser.add_argument(
		'-l', '--leading',
		dest = 'leading_space',
		action = 'store_true',
		required = False,
		default = False,
		help = 'strip leading spaces from file/directory names',
		)

	parser.add_argument(
		'-t', '--trailing',
		dest = 'trailing_space',
		action = 'store_true',
		required = False,
		default = False,
		help = 'strip trailing spaces from file/directory names',
		)

	parser.add_argument(
		'-e', '--extension',
		dest = 'ext_space',
		action = 'store_true',
		required = False,
		default = False,
		help = 'strip spaces before and after the file extension dot',
		)

	parser.add_argument(
		'-u', '--uglies',
		dest = 'remove_uglies',
		action = 'store_true',
		required = False,
		default = False,
		help = 'replace ugly characters with underscores',
		)

	parser.add_argument(
		'-v', '--verbose',
		dest = 'verbose',
		action = 'store_true',
		required = False,
		default = False,
		help = 'get verbose output from the logger',
		)

	parser.add_argument(
		'-q', '--quiet',
		dest = 'quiet',
		action = 'store_true',
		required = False,
		default = False,
		help = 'supress console output except errors',
		)

	parser.add_argument(
		'--dryrun',
		dest = 'dryrun',
		action = 'store_true',
		required = False,
		default = False,
		help = 'perform a dry run without actually changing anything',
		)

	parser.add_argument(
		'--logfile',
		dest = 'logfile',
		required = False,
		default = None,
		metavar = '<log file>',
		help = 'a log file to use',
		)

	parser.add_argument(
		'-c', '--config',
		dest = 'configfile',
		required = False,
		default = None,
		metavar = '<config file>',
		help = 'a config file to use',
		)

	parser.add_argument(
		'-p', '--parameters',
		dest = 'param',
		action = 'store_true',
		required = False,
		default = False,
		help = 'dump cli parameters and exit',
		)

	parser.add_argument(
		'-s', '--stats',
		dest = 'stats',
		action = 'store_true',
		required = False,
		default = False,
		help = 'show statistics on modifications',
		)

	parser.add_argument(
		dest = 'workpath',
		metavar = '<path to process>',
		help = 'given path will be processed for sanatizing names'
		)

	args = parser.parse_args()


def setupLogging():

	global logger
	log_encoding='utf-8'
	logger = logging.getLogger('macSanitize')
	logger.setLevel(logging.DEBUG)

	# add console logger
	if not args.quiet:
		c_handler = logging.StreamHandler()
		c_formatter = logging.Formatter('[%(levelname)s] %(message)s')
		c_handler.setFormatter(c_formatter)
		if args.verbose:
			c_handler.setLevel(logging.DEBUG)
		else:
			c_handler.setLevel(logging.INFO)
		logger.addHandler(c_handler)

	# log to file if logfile parameter is given
	if args.logfile:
		f_handler = ownedFileHandler(args.logfile, mode='w', encoding=log_encoding)
		f_formatter = logging.Formatter('[%(levelname)s] %(message)s')
		f_handler.setFormatter(f_formatter)
		if args.verbose:
			f_handler.setLevel(logging.DEBUG)
		else:
			f_handler.setLevel(logging.INFO)
		logger.addHandler(f_handler)


def getConfigList(config, sect, opt):

	opt_str = config.get(sect, opt)
	opt_str = opt_str.strip()
	if not opt_str: return []
	list_delim = opt_str[0:1]
	opt_str = opt_str[1:]
	return [ e.strip() for e in opt_str.split(list_delim) ]


def getConfig(configfile):

	global config
	global re_l_space
	global re_t_space
	global re_uglies
	global re_filename
	global replacement
	global folder_skiplist
	global file_skiplist

	config = configparser.ConfigParser()

	try:
		if configfile and os.path.exists(configfile):
			logger.info('Reading config file: {0}'.format(configfile))
			config.read(configfile)

		elif os.path.exists('/etc/macSanitize.ini'):
			logger.info('Reading config file: {0}'.format(configfile))
			config.read('/etc/macSanitize.ini')

	except configparser.Error as e:
		logger.error(e)
		sys.exit(1)

	# get uglies
	try:
		u = config.get('macSanitize', 'uglies')

		try:
			re_uglies = re.compile('([{0}]+)'.format(u))
			logger.info('using uglies from config: {0}'.format(u))

		except re.error:
			logger.error('Failed to compile uglies regex from config')
			sys.exit(1)

	except configparser.Error as e:
		logger.debug('{0} - using default uglies: "|\\:*?<>'.format(e))
		re_uglies = re.compile(uglies)

	# get replacement character
	try:
		replacement = config.get('macSanitize', 'replacement')
		logger.info('using replacement character from config: {0}'.format(replacement))

	except configparser.Error as e:
		logger.debug('{0} - using default replacement character: _'.format(e))
		replacement = '_'

	# get skiplists
	try:
		folder_skiplist = getConfigList(config, 'macSanitize', 'folder skiplist')
		logger.info('using folder skiplist from config: {0}'.format(folder_skiplist))

	except configparser.Error as e:
		folder_skiplist = ['.AppleDouble', ]
		logger.debug('{0} - using default folder skiplist {1}'.format(e, folder_skiplist))

	try:
		file_skiplist = getConfigList(config, 'macSanitize', 'file skiplist')
		logger.info('using file skiplist from config: {0}'.format(file_skiplist))

	except configparser.Error as e:
		file_skiplist = []
		logger.debug('{0} - using default file skiplist {1}'.format(e, file_skiplist))

	# compile regular expressions
	re_l_space = re.compile(l_space)
	re_t_space = re.compile(t_space)
	re_filename = re.compile(filename)


def doNameList(fob, skiplist, file=True):

	global mod
	bpath = fob[0]

	# work on a copy in dryrun, but descend the original
	# only modify fob list for skipping elements
	if args.dryrun:
		fob_a = deepcopy(fob)
	else:
		fob_a = fob

	# processing elements from fob[ln] 1=dirs, 2=files
	if file:
		ln = 2
		t = 'file'
	else:
		ln = 1
		t = 'directory'

	for fn in range(0, len(fob[ln])):

		mod = False
		ntotal[ln] += 1

		# skip elements in list
		sn = fob_a[ln][fn]
		if sn in skiplist:
			logger.debug("skipping {0}: '{1}'".format(t, os.path.join(bpath, sn)))
			del fob_a[ln][fn]
			if args.dryrun: del fob[ln][fn]
			nskip[ln] += 1
			continue

		# remove leading spaces
		if args.leading_space:
			sn = fob_a[ln][fn]
			f_match = re_l_space.fullmatch(sn)
			if f_match:
				sl = len(f_match.groups()[0])
				dn = sn[sl:]
				logger.debug("leading space in {0}: '{1}'".format(t, os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob_a, fn, dn, file)

		# remove trailing spaces
		if args.trailing_space:
			sn = fob_a[ln][fn]
			f_match = re_t_space.fullmatch(sn)
			if f_match:
				sl = len(f_match.groups()[0])
				dn = sn[:-sl]
				logger.debug("trailing space in {0}: '{1}'".format(t, os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob_a, fn, dn, file)

		# remove ugly characters
		if args.remove_uglies:
			sn = fob_a[ln][fn]
			f_match = re_uglies.search(sn)
			if f_match:
				dn = re_uglies.sub(replacement, sn)
				logger.debug("ugly character in {0}: '{1}'".format(t, os.path.join(bpath, sn)))
				fileRename(fob_a, fn, dn, file)

		# continue loop here for directories as they don't have file extensions
		if not file:
			if mod: nren[ln] += 1
			continue

		# remove extension spaces
		if not args.ext_space: continue

		sn = fob_a[ln][fn]
		f_match = re_filename.fullmatch(sn)

		if f_match:
			# remove trailing spaces in file base name before the extension dot
			sn_lst = f_match.groups()
			f_match2 = re_t_space.fullmatch(sn_lst[0])
			if f_match2:
				sl = len(f_match2.groups()[0])
				dn = '.'.join( [sn_lst[0][:-sl], sn_lst[1],] )
				logger.debug("trailing base name space in {0}: '{1}'".format(t, os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob_a, fn, dn, file)

		sn = fob_a[ln][fn]
		f_match = re_filename.fullmatch(sn)

		if f_match:
			# remove spaces leading the extension after the dot
			sn_lst = f_match.groups()
			f_match2 = re_l_space.fullmatch(sn_lst[1])
			if f_match2:
				sl = len(f_match2.groups()[0])
				dn = '.'.join( [sn_lst[0], sn_lst[1][sl:],] )
				logger.debug("leading extension space in {0}: '{1}'".format(t, os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob_a, fn, dn, file)

		if mod: nren[ln] += 1


def fileRename(fob, fn, dn, file=True):

	global mod

	if file:
		ln = 2
		f_match = re_filename.fullmatch(dn)
		t = 'file'
	else:
		ln = 1
		f_match = None
		t = 'directory'

	sn = fob[ln][fn]
	bpath = fob[0]

	try:
		dn_lst = f_match.groups()
	except AttributeError:
		dn_lst = [dn, ]

	count = 1
	dn_lst_new = list(dn_lst)

	while True:
		dn_new = '.'.join(dn_lst_new)
		if dn_new in fob[1] + fob[2]:
			dn_lst_new[0] = dn_lst[0] + str(count)
			count += 1
		else:
			break

	fsn = os.path.join(bpath, sn)
	fdn = os.path.join(bpath, dn_new)
	logger.info("renaming {0} '{1}' to '{2}'".format(t, fsn, fdn))

	ren = True
	if not args.dryrun:
		if not os.path.exists(fsn):
			logger.error("unable to rename {0} '{1}' to '{2}', as source doesn't extists".format(t, fsn, fdn))
			ren = False
		elif os.path.exists(fdn):
			logger.error("unable to rename {0} '{1}' to '{2}', as destination already extists".format(t, fsn, fdn))
			ren = False
		else:
			try:
				os.rename(fsn, fdn)
			except:
				logger.error("failed to rename {0} '{1}' to '{2}'")
				ren = False
				nfail[ln] += 1

	if ren:
		fob[ln][fn] = dn_new
		mod = True
		nmod[ln] += 1


if __name__ == '__main__':

	# get command line arguments
	getArgs()

	if args.param:
		for name in vars(args):
			print(name + ' : ' + str(vars(args)[name]))
		sys.exit(0)

	# exit if workpath doesn't exist
	if not os.path.exists(args.workpath):
		print("work path does not exist: '{0}'".format(args.workpath))
		sys.exit(1)

	# setup logging
	setupLogging()

	# read config file if existent
	getConfig(args.configfile)

	# walk trough the path structure
	for fob in os.walk(args.workpath):

		if args.process_files:
			doNameList(fob, file_skiplist)

		if args.process_dirs:
			doNameList(fob, folder_skiplist, False)

	if args.stats:
		logger.info('Statistics --------------------')
		logger.info('dir total:         {0}'.format(ntotal[1]))
		logger.info('dir skip:          {0}'.format(nskip[1]))
		logger.info('dir modification:  {0}'.format(nmod[1]))
		logger.info('dir mod failed:    {0}'.format(nfail[1]))
		logger.info('dir renamed:       {0}'.format(nren[1]))
		logger.info('file total:        {0}'.format(ntotal[2]))
		logger.info('file skip :        {0}'.format(nskip[2]))
		logger.info('file modification: {0}'.format(nmod[2]))
		logger.info('file mod failed:   {0}'.format(nfail[2]))
		logger.info('file renamed:      {0}'.format(nren[2]))

