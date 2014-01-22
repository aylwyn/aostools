#!/software/bin/python
# Aylwyn Scally 2014

import sys
import getopt
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
#from bputil import *

# global defaults
sim = 0
loglevel = logging.WARNING
bsub_args = ''
memG = 0
nthreads = 1
replace = False
output = True
rerun = False
berr_suffix = '.berr'
bout_suffix = '.bout'
jobname = ''
outname = ''
grpname = 'rdgroup'

os.umask(0002)

def usage():
	print('usage: %s cmd [-A bsub_args] [-q bsub_queue] [-M memlimit_Gb] [-t nthreads] [-o output_name] [-j jobname] [-g group] [--replace] [--sim | --simv] [-v]' % (os.path.basename(sys.argv[0])))
	sys.exit(2)

try:
	opts, args = getopt.gnu_getopt(sys.argv[1:], 'A:j:M:o:q:t:v', ['replace', 'sim', 'simv', 'simq', 'debug', 'rerun', 'no_output'])
except getopt.GetoptError:
	usage()
	sys.exit(2)
#popts = []
for (oflag, oarg) in opts:
	if oflag == '--sim':
		sim = 2
	if oflag == '--simq':
		sim = 1
		loglevel = logging.WARNING
	if oflag == '--simv':
		sim = 1
		loglevel = logging.INFO
	if oflag == '--no_output':
		output = False
	if oflag == '--replace':
		replace = True
	elif oflag == '-q':
		bsub_args += ' -q ' + oarg + ' '
	elif oflag == '-o':
		outname = oarg
	elif oflag == '-j':
		jobname = oarg
	elif oflag == '-g':
		grpname = oarg
	elif oflag == '-M':
		memG = eval(oarg)
	elif oflag == '-t':
		nthreads = int(oarg)
	elif oflag == '-A':
		bsub_args = oarg
	elif oflag == '-v':
		loglevel = logging.INFO
	elif oflag == '--debug':
		loglevel = logging.DEBUG
	elif oflag == '--rerun':
		rerun = True
#	else:
#		popts.append((oflag, oarg))

logging.basicConfig(format = '%(module)s:%(lineno)d:%(levelname)s: %(message)s', level = loglevel)

memM = memG * 1e3
memk = memG * 1e6
memstr = str(memG)
if memG > 0:
	bsub_args += '-M%d -R"select[mem>%d] rusage[mem=%d]" ' % (memM, memM, memM)
	memstr += 'G'

if nthreads > 1:
	bsub_args += '-n%d -R"span[hosts=1]" ' % nthreads

if len(args) < 1:
	usage()

if outname:
	bout = outname + bout_suffix
	if output:
		args += ['>', outname]
	if os.path.exists(outname) and not replace:
		if not rerun:
			warning('%s exists; use --replace' % outname)
		sys.exit(2)
	if not sim and os.path.exists(bout):
		info('removing %s' % bout)
		os.remove(bout)
	#if not sim and os.path.exists(berr):
	#	os.remove(berr)
else:
#	stardate = strftime("%y%m%d-%H%M%S")
	stardate = strftime("%y%m%d-%H%M")
#	stardate = ''.join([hex(int(strftime(x)))[2:] for x in ['%y', '%m', '%d', '%H', '%M', '%S']]).upper()

#	cmdtoks = [os.path.basename(x).translate(string.maketrans("",""), string.punctuation) for x in args[0].split()]
#	cmdstr = ''.join([x[0] for x in cmdtoks if x])
#	cmdstr = cmdstr.translate(string.maketrans("",""), string.punctuation)
#	cmdstr = os.path.basename(args[0].split()[0])
	cmdhash = str(hash(args[0]))
	cmdstr = cmdhash[-6:] + '-' + memstr
	bout = stardate + '-' + cmdstr + bout_suffix
cmd = 'bsub -o %s -G %s ' % (bout, grpname)
#cmd = 'bsub -o %s ' % (bout)
if jobname:
	cmd += '-J"%s" ' % (jobname)
cmd += '%s \'%s\'' % (bsub_args, ' '.join(args))

info('submitting \'%s\'; output in %s' % (' '.join(args), bout))
subcall(cmd, sim, wait = True)
