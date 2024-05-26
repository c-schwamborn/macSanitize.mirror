#!/usr/bin/env python3
# coding:utf-8
#

import os
import sys
import re
import logging
from copy import deepcopy 
import argparse
import textwrap
import pwd, grp

# TODO: implement parameters for:
# extension_length = 6
# replacement = '_'
# uglies = r'(["|\\:*?<>]+)'
# folder_skiplist


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


# setup command line arguments
parser = argparse.ArgumentParser(
	formatter_class=argparse.RawDescriptionHelpFormatter,
	description=textwrap.dedent('''\
		macSanitize will help you to remove characters from file or
		directory names that violates the smb standard and will
		therfore result in empty directories or being invisible when
		shared by samba.
		It can also remove leading/trailing spaces also causing files
		and directories not as expected.
		Most common cause for those names, are file and directoy
		originating on Apple computers, as those system allow anything
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
	default = True,
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
	'-p', '--parameters',
	dest = 'param',
	action = 'store_true',
	required = False,
	default = False,
	help = 'dump cli parameters and exit',
	)

parser.add_argument(
	dest = 'workpath',
	metavar = '<path to process>',
	help = 'given path will be processed for sanatizing names'
	)

args = parser.parse_args()

if args.param:
	for name in vars(args):
		print(name + ' : ' + str(vars(args)[name]))
	sys.exit(0)

if not os.path.exists(args.workpath):
	print("work path does not exist: '{0}'".format(args.workpath))
	sys.exit(1)

folder_skiplist = (
	'.AppleDouble',
)

# reqular expressions
l_space = r'^(\s+).*$'
t_space = r'^.*[^\s](\s+)$'
uglies = r'(["|\\:*?<>]+)'
filename = r'^(.*[^.])\.(\s*\w{1,6})$'
re_l_space = re.compile(l_space)
re_t_space = re.compile(t_space)
re_uglies = re.compile(uglies)
re_filename = re.compile(filename)

# setup logging
log_encoding='utf-8'
logger = logging.getLogger('macSanitize')
logger.setLevel(logging.DEBUG)

# add console logger
if not args.quiet:
	c_handler = logging.StreamHandler()
	c_formatter = logging.Formatter('%(levelname)s - %(message)s')
	c_handler.setFormatter(c_formatter)
	if args.verbose:
		c_handler.setLevel(logging.DEBUG)
	else:
		c_handler.setLevel(logging.INFO)
	logger.addHandler(c_handler)

# log to file if logfile parameter is given
if args.logfile:
	f_handler = ownedFileHandler(args.logfile, mode='w', encoding=log_encoding)
	f_formatter = logging.Formatter('%(asctime)s - %(levelname)s ' +
		'[%(module)s/%(funcName)s/%(lineno)d] %(message)s')
	f_handler.setFormatter(f_formatter)
	if args.verbose:
		f_handler.setLevel(logging.DEBUG)
	else:
		f_handler.setLevel(logging.INFO)
	logger.addHandler(f_handler)



def doFiles(fob):

	# processing files
	bpath = fob[0]
	for fn in range(0, len(fob[2])):

		# remove leading spaces in files
		if args.leading_space:
			sn = fob[2][fn]
			f_match = re_l_space.fullmatch(sn)
			if f_match:
				sl = len(f_match.groups()[0])
				dn = sn[sl:]
				logger.debug("leading space in file: '{0}'".format(os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob, fn, dn)

		# remove trailing spaces in files
		if args.trailing_space:
			sn = fob[2][fn]
			f_match = re_t_space.fullmatch(sn)
			if f_match:
				sl = len(f_match.groups()[0])
				dn = sn[:-sl]
				logger.debug("trailing space in file: '{0}'".format(os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob, fn, dn)

		# remove extension spaces
		if args.ext_space:

			sn = fob[2][fn]
			f_match = re_filename.fullmatch(sn)

			if f_match:
				# remove trailing spaces in file name base before extension
				sn_lst = f_match.groups()
				f_match2 = re_t_space.fullmatch(sn_lst[0])
				if f_match2:
					sl = len(f_match2.groups()[0])
					dn = '.'.join( [sn_lst[0][:-sl], sn_lst[1],] )
					logger.debug("trailing base name space in file: '{0}'".format(os.path.join(bpath, sn)))
					logger.debug("space lengh: {0}".format(sl))
					fileRename(fob, fn, dn)

			sn = fob[2][fn]
			f_match = re_filename.fullmatch(sn)

			if f_match:
				# remove spaces leading the extension
				sn_lst = f_match.groups()
				f_match2 = re_l_space.fullmatch(sn_lst[1])
				if f_match2:
					sl = len(f_match2.groups()[0])
					dn = '.'.join( [sn_lst[0], sn_lst[1][sl:],] )
					logger.debug("leading extension space in file: '{0}'".format(os.path.join(bpath, sn)))
					logger.debug("space lengh: {0}".format(sl))
					fileRename(fob, fn, dn)

		# remove ugly characters in files
		if args.remove_uglies:
			sn = fob[2][fn]
			f_match = re_uglies.search(sn)
			if f_match:
				dn = re_uglies.sub('_', sn)
				logger.debug("ugly character in file: '{0}'".format(os.path.join(bpath, sn)))
				fileRename(fob, fn, dn)


def doDirectories(fob):

	# processing directories
	bpath = fob[0]
	if args.dryrun:
		fob_a = deepcopy(fob)
	else:
		fod_a = fob

	for fn in range(0, len(fob[1])):

		sn = fob[1][fn]
		if sn in folder_skiplist:
			logger.debug("skipping directory: '{0}'".format(os.path.join(bpath, sn)))
			del fob[1][fn]
			continue

		# remove leading spaces in directories
		if args.leading_space:
			sn = fob[1][fn]
			f_match = re_l_space.fullmatch(sn)
			if f_match:
				sl = len(f_match.groups()[0])
				dn = sn[sl:]
				logger.debug("leading space in directory: '{0}'".format(os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob_a, fn, dn, False)

		# remove trailing spaces in files
		if args.trailing_space:
			sn = fob[1][fn]
			f_match = re_t_space.fullmatch(sn)
			if f_match:
				sl = len(f_match.groups()[0])
				dn = sn[:-sl]
				logger.debug("trailing space in directory: '{0}'".format(os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob_a, fn, dn, False)

		# remove ugly characters in files
		if args.remove_uglies:
			sn = fob[1][fn]
			f_match = re_uglies.search(sn)
			if f_match:
				dn = re_uglies.sub('_', sn)
				logger.debug("ugly character in directory: '{0}'".format(os.path.join(bpath, sn)))
				fileRename(fob_a, fn, dn, False)


def fileRename(fob, fn, dn, file=True):

	lobj = 1
	if file: lobj = 2

	fob_list = fob[lobj]
	sn = fob_list[fn]
	bpath = fob[0]

	if lobj == 2:
		f_match = re_filename.fullmatch(dn)
		t = 'file'
	else:
		f_match = None
		t = 'directory'

	try:
		dn_lst = f_match.groups()
	except AttributeError:
		dn_lst = [dn, ]

	count = 1
	dn_lst_new = list(dn_lst)

	while True:
		dn_new = '.'.join(dn_lst_new)
		if dn_new in fob_list:
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

	if ren:
		fob[lobj][fn] = dn_new


if __name__ == '__main__':

	# walk trough the path structure
	for fob in os.walk(args.workpath):

		if args.process_files:
			doFiles(fob)

		if args.process_dirs:
			doDirectories(fob)


