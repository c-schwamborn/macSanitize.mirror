#!/usr/bin/env python3
# coding:utf-8
#

import os
import re
import logging

##
# from shell find experiments:
# to find everything ugly: '^.*/( .*|.* |.* \..+|.*["|\\:*?<>].*)$'
# remove: ' .*|.* '
# do we remove spaces before the file extension? '.* \..+'
#   can we identify the extension correctly?
# replace: ["|\\:*?<>]
# important: handle already existing files!!!

# shutil.move(source, target)
# os.rename(src, dst)
# os.listdir(os.getcwd())

# os.walk(top, topdown=True, onerror=None, followlinks=False)
# yields a 3-tuple: dirpath, dirnames, filenames


verbose = True
dryrun = True

process_files = True
process_directories = False

leading_space = True
trailing_space = True
extension_space = True
remove_uglies = True

# TODO:
#extension_length = 6

#search_path = "/home/cs/projects/macSanitize/pathrename"
#search_path = "/home/cs/projects/macSanitize/sonderzeichen"
search_path = "/home/cs/projects/macSanitize/multiname"
folder_skiplist = (
	'.AppleDouble',
)

# reqular expressions
l_space = r'^(\s+).*$'
re_l_space = re.compile(l_space)
t_space = r'^.*[^\s](\s+)$'
re_t_space = re.compile(t_space)
uglies = r'(["|\\:*?<>]+)'
re_uglies = re.compile(uglies)
filename = r'^(.*[^.])\.(\s*\w{1,6})$'
re_filename = re.compile(filename)

# setup logging
logger = logging.getLogger('macSanitize')
logger.setLevel(logging.DEBUG)
c_handler = logging.StreamHandler()
c_formatter = logging.Formatter('%(levelname)s - %(message)s')
c_handler.setFormatter(c_formatter)
if verbose:
	c_handler.setLevel(logging.DEBUG)
else:
	c_handler.setLevel(logging.INFO)
logger.addHandler(c_handler)


def doFiles(fob):

	# processing files
	bpath = fob[0]
	for fn in range(0, len(fob[2]) - 1):

		sn = fob[2][fn]

		# remove leading spaces in files
		if leading_space:
			f_match = re_l_space.fullmatch(sn)
			if f_match:
				sl = len(f_match.groups()[0])
				dn = sn[sl:]
				logger.debug("leading space in file: '{0}'".format(os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob, fn, dn)

		# remove trailing spaces in files
		if trailing_space:
			f_match = re_t_space.fullmatch(sn)
			if f_match:
				sl = len(f_match.groups()[0])
				dn = sn[:-sl]
				logger.debug("trailing space in file: '{0}'".format(os.path.join(bpath, sn)))
				logger.debug("space lengh: {0}".format(sl))
				fileRename(fob, fn, dn)

		# remove extension spaces
		if extension_space:

			f_match = re_filename.fullmatch(sn)

			if f_match:
				sn_lst = f_match.groups()

				# remove trailing spaces in file name base before extension
				f_match2 = re_t_space.fullmatch(sn_lst[0])
				if f_match2:
					sl = len(f_match2.groups()[0])
					dn = '.'.join( [sn_lst[0][:-sl], sn_lst[1],] )
					logger.debug("trailing base name space in file: '{0}'".format(os.path.join(bpath, sn)))
					logger.debug("space lengh: {0}".format(sl))
					fileRename(fob, fn, dn)

				# remove spaces leading the extension
				f_match2 = re_l_space.fullmatch(sn_lst[1])
				if f_match2:
					sl = len(f_match2.groups()[0])
					dn = '.'.join( [sn_lst[0], sn_lst[1][sl:],] )
					logger.debug("leading extension space in file: '{0}'".format(os.path.join(bpath, sn)))
					logger.debug("space lengh: {0}".format(sl))
					fileRename(fob, fn, dn)

		# remove ugly characters in files
		if remove_uglies:
			f_match = re_uglies.search(sn)
			if f_match:
				dn = re_uglies.sub('_', sn)
				logger.debug("ugly character in file: '{0}'".format(os.path.join(bpath, sn)))
				fileRename(fob, fn, dn)


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
	logger.info("renaming: '{0}' to '{1}'".format(fsn, fdn))

	ren = True
	if not dryrun:
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
	for fob in os.walk(search_path):

		if process_files:
			doFiles(fob)


