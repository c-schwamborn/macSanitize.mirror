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

leading_space = False
trailing_space = False
extension_space = True
remove_uglies = False

#search_path = "/home/cs/projects/macSanitize/pathrename"
#search_path = "/home/cs/projects/macSanitize/sonderzeichen"
search_path = "/home/cs/projects/macSanitize/multiname"
folder_skiplist = (
	'.AppleDouble',
	)

l_space = r'^( +).*$'
re_l_space = re.compile(l_space)
t_space = r'^.*[^ ]( +)$'
re_t_space = re.compile(t_space)
uglies = r'(["|\\:*?<>]+)'
re_uglies = re.compile(uglies)
filename = r'^(.*[^.])\.(\s*\w{1,6})$'
re_filename = re.compile(filename)


def fileRename(base_path, fob_list, sn, dn):


	f_match = re_filename.fullmatch(dn)
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

	fsn = os.path.join(base_path, sn)
	fdn = os.path.join(base_path, dn_new)

	logger.info("renaming: '{0}' to '{1}'".format(fsn, fdn))

	if not dryrun:
		if not os.path.exists(fsn):
			ogger.error("unable to rename file '{0}' to '{1}', as source doesn't extists".format(fsn, fdn))
		elif os.path.exists(fdn):
			logger.error("unable to rename file '{0}' to '{1}', as destination already extists".format(fsn, fdn))
		else:
			os.rename(fsn, fdn)

	return dn_new


if __name__ == '__main__':

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

	# walk trough the path structure
	for fob in os.walk(search_path):

		#print('------------before-----------')
		#print(fob)

		# processing files
		for fn in range(0, len(fob[2]) - 1):

			# remove leading spaces in files
			if leading_space:
				f_match = re_l_space.fullmatch(fob[2][fn])
				if f_match:
					sl = len(f_match.groups()[0])
					sn = fob[2][fn]
					fsn = os.path.join(fob[0], sn)
					dn = sn[sl:]
					logger.debug("leading space in: '{0}'".format(fsn))
					logger.debug("space lengh: {0}".format(sl))
					dn_new = fileRename(fob[0], fob[2], sn, dn)
					fob[2][fn] = dn_new

			# remove trailing spaces in files
			if trailing_space:
				f_match = re_t_space.fullmatch(fob[2][fn])
				if f_match:
					sl = len(f_match.groups()[0])
					sn = fob[2][fn]
					fsn = os.path.join(fob[0], sn)
					dn = sn[:-sl]
					logger.debug("trailing space in: '{0}'".format(fsn))
					logger.debug("space lengh: {0}".format(sl))
					dn_new = fileRename(fob[0], fob[2], sn, dn)
					fob[2][fn] = dn_new

			# remove extension spaces
			if extension_space:

				f_match = re_filename.fullmatch(fob[2][fn])

				if f_match:
					sn_lst = f_match.groups()

					# remove trailing spaces in file name base before extension
					f_match2 = re_t_space.fullmatch(sn_lst[0])
					if f_match2:
						sl = len(f_match2.groups()[0])
						sn = fob[2][fn]
						fsn = os.path.join(fob[0], sn)
						dn = '.'.join( [sn_lst[0][:-sl], sn_lst[1],] )
						logger.debug("trailing base name space in: '{0}'".format(fsn))
						logger.debug("space lengh: {0}".format(sl))
						dn_new = fileRename(fob[0], fob[2], sn, dn)
						fob[2][fn] = dn_new

					# remove spaces leading the extension
					f_match2 = re_l_space.fullmatch(sn_lst[1])
					if f_match2:
						sl = len(f_match2.groups()[0])
						sn = fob[2][fn]
						fsn = os.path.join(fob[0], sn)
						dn = '.'.join( [sn_lst[0], sn_lst[1][sl:],] )
						logger.debug("leading extension space in: '{0}'".format(fsn))
						logger.debug("space lengh: {0}".format(sl))
						dn_new = fileRename(fob[0], fob[2], sn, dn)
						fob[2][fn] = dn_new

			# remove ugly characters in files
			if remove_uglies:
				f_match = re_uglies.search(fob[2][fn])
				if f_match:
					sn = fob[2][fn]
					fsn = os.path.join(fob[0], sn)
					dn = re_uglies.sub('_', sn)
					logger.debug("ugly character in: '{0}'".format(fsn))
					dn_new = fileRename(fob[0], fob[2], sn, dn)
					fob[2][fn] = dn_new


		continue

		for fn in range(0, len(fob[1]) - 1):

			if fob[1][fn] in folder_skiplist:

				print("skipping: {0}".format(fob[1][fn]))
				del fob[1][fn]
				continue

			if fob[1][fn] == "p1":

				print("renaming: {0} to {1}".format(fob[1][fn], 'p1_new'))
				os.rename(os.path.join(fob[0], fob[1][fn]), os.path.join(fob[0], 'p1_new'))
				fob[1][fn] = 'p1_new'


		#print('------------after-----------')
		#print(fob)



