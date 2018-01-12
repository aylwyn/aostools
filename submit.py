#!/usr/bin/env python
# Aylwyn Scally 2014

import sys
import argparse
import subprocess
import os
import os.path
from time import strftime
import logging
from logging import error, warning, info, debug, critical
#import re
#import locale
import string

#locale.setlocale(locale.LC_ALL, 'en_GB')

from aosutils import *

bout_suffix = '.bout'
outname = ''

#os.umask(0002)

def setname(args, suffix):
	if args.outname:
		rname = args.outname + suffix
	else:
		stardate = strftime("%y%m%d-%H%M")
		cmdhash = str(hash(args.ARG[0]))
		memstr = str(args.memG)
		memstr += 'G'
		cmdstr = cmdhash[-6:] + '-' + memstr
		rname = stardate + '-' + cmdstr + suffix
	return(rname)

def checkclear(args, bout):
	if not args.no_output and args.outname:
		if os.path.exists(args.outname) and not args.replace:
			if not args.rerun:
				warning('%s exists; use --replace' % args.outname)
			sys.exit(2)
	else:
		if os.path.exists(bout) and not args.replace:
			if not args.rerun:
				warning('%s exists; use --replace' % bout)
			sys.exit(2)
	if not args.sim and os.path.exists(bout):
		info('removing %s' % bout)
		os.remove(bout)

def nohup(args):
	bout = setname(args, bout_suffix)
	if args.outname and not args.no_output:
		if args.zipout:
			args.outname += '.gz'
#			args.ARG += ['2>', bout, '| gzip >', args.outname]
			args.ARG += ['| gzip >', args.outname]
		else:
#			args.ARG += ['2>', bout, '1>', args.outname]
			args.ARG += ['>', args.outname]
	checkclear(args, bout)

	cmd = ' '.join(args.ARG)
	cmdname = setname(args, '.cmd')
	if not args.sim:
		cmdfile = open(cmdname, 'w')
		cmdfile.write(cmd + '\n')
		cmdfile.close()

	info('submitting \'%s\'; output in %s' % (cmd, bout))
	p = subcall('nohup bash %s > %s 2>&1' % (cmdname, bout) , args.sim)
	if not args.sim:
		info('process %s' % p.pid)

def bsub(args):
#	if args.memG > 0.0:
	memM = args.memG * 1e3
	memk = args.memG * 1e6
	args.bsub_args += '-M%d -R"select[mem>%d] rusage[mem=%d]" ' % (memM, memM, memM)

	if args.threads > 1:
		args.bsub_args += '-n%d -R"span[hosts=1]" ' % args.threads

	bout = setname(args, bout_suffix)
	if args.outname and not args.no_output:
		if args.zipout:
			args.outname += '.gz'
			args.ARG += ['| gzip >', args.outname]
		else:
			args.ARG += ['>', args.outname]
	checkclear(args, bout)
	cmd = 'bsub -o %s -G %s ' % (bout, args.grpname)
	if args.jobname:
		cmd += '-J"%s" ' % (args.jobname)
	cmd += '%s "%s"' % (args.bsub_args, ' '.join(args.ARG))

	info('submitting \'%s\'; output in %s' % (' '.join(args.ARG), bout))
	subcall(cmd, args.sim, wait = True)

pp = argparse.ArgumentParser(add_help=False)
pp.add_argument('--replace', action='store_true', default = False, help = 'replace existing files')
pp.add_argument('--rerun', action='store_true', default = False)#, help = 'rerunning')
pp.add_argument('--sim', action='store_true', default = False, help = 'dry run')
pp.add_argument('-v', '--verbose', action='store_true', default = False)
pp.add_argument('--debug', action='store_true', default = False, help=argparse.SUPPRESS)
pp.add_argument('-o', '--outname', default = '', help='output file name (used for bout file if --no_output)')
pp.add_argument('--no_output', action='store_true', default = False, help='cmd has no output')
pp.add_argument('-z', '--zipout', action='store_true', default = False, help='pipe output through gzip')
pp.add_argument('ARG', nargs='*', help='command arguments to execute')

p = argparse.ArgumentParser()
s = p.add_subparsers()

p1 = s.add_parser('nohup', parents=[pp], help='simple execution with nohup')#, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
#p1.add_argument('-d', '--dirpref', help='directory name prefix')
p1.add_argument('-M', '--memG', type=float, default = 2.0, help=argparse.SUPPRESS)#TODO 'GB of RAM to use')
p1.add_argument('-j', '--jobname', help=argparse.SUPPRESS)#TODO
p1.set_defaults(func=nohup)

p2 = s.add_parser('bsub', parents=[pp], help='submit to bsub')#, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
#p2.add_argument('DIR')
#p2.add_argument('--parfile', default='', help='input parameter file (eigenstrat)')
p2.add_argument('-t', '--threads', type=int, help = 'number of threads to use')
p2.add_argument('-q', '--queue', default='normal')#, help = 'queue to use')
p2.add_argument('-g', '--grpname', default='rdgroup')#, help = 'queue to use')
p2.add_argument('-j', '--jobname')#, help = 'jobname to use')
p2.add_argument('-M', '--memG', type=float, default = 2.0, help = 'GB of RAM to use')
p2.add_argument('-A', '--bsub_args', default = '', help = 'additional bsub arguments')
p2.set_defaults(func=bsub)

args = p.parse_args()

loglevel = logging.WARNING 
if args.verbose: 
    loglevel = logging.INFO 
if args.debug: 
    loglevel = logging.DEBUG 
logging.basicConfig(format = '%(module)s:%(lineno)d:%(levelname)s: %(message)s', level = loglevel) 
 
args.func(args)


