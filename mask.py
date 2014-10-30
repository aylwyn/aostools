#!/usr/bin/env python
# Aylwyn Scally 2014

import sys
import getopt
#import os
import os.path
import gzip
import logging
from logging import error, warning, info, debug, critical
import argparse
from bisect import bisect

#	if oflag == '--ucsc':
#		mchr = 1
#		mpos = (2,3)

p = argparse.ArgumentParser()
p.add_argument('MASK_FILE', nargs = '*') 
#p.add_argument('--sim', action='store_true', default = False, help = 'dry run')
p.add_argument('-v', '--verbose', action='store_true', default = False)#, help = 'dry run')
p.add_argument('--debug', action='store_true', default = False, help=argparse.SUPPRESS)
p.add_argument('--bed', action='store_true', default = False, help= 'mask in bed format')
p.add_argument('--mchr', type=int, default=1, help = 'chr column in MASK_FILE')
p.add_argument('--mpos', default='2,3', help = '"start,end" pos columns in MASK_FILE')
#pp.add_argument('--ucsc', action='store_true', default = False, help= 'mask in UCSC format')
p.add_argument('--info', action='store_true', default = False, help= 'print mask stats')
p.add_argument('--ovlap', action='store_true', default = False, help= 'output overlap mask')
p.add_argument('--flatten', action='store_true', default = False, help= 'output flattened mask')

#s = p.add_subparsers(help='sub-command help')
#p1 = s.add_parser('apply', help='apply mask to target file/stream')
#p.add_argument('TARGET_FILE', nargs='?') 
p.add_argument('-a', '--apply_to', default = '', dest = 'TARGET_FILE', help = 'apply mask as filter to TARGET_FILE ("-" for stdin")') 
#p.add_argument('-s', '--skiplines', type=int, default=0, help = 'number of initial lines to skip in TARGET_FILE')
p.add_argument('--tchr', type=int, default=1, help = 'chr column in TARGET_FILE')
p.add_argument('--tpos', type=int, default=2, help = 'pos column in TARGET_FILE')
#p1.add_argument('--spos', default='2,3', help = 'start,end pos columns in TARGET_FILE')

args = p.parse_args()

loglevel = logging.WARNING
if args.verbose:
	loglevel = logging.INFO
if args.debug:
	loglevel = logging.DEBUG
logging.basicConfig(format = '%(module)s:%(lineno)d:%(levelname)s: %(message)s', level = loglevel)

args.mchr -= 1
mpos = [int(x) - 1 for x in args.mpos.split(',')]
args.tchr -= 1
args.tpos -= 1

#read masks
mblocks = {}
for mfile in args.MASK_FILE:
	info('Reading %s' % mfile)
	if mfile.endswith('.gz'):
		mlines = (line.split() for line in gzip.open(mfile) if not line.startswith('#'))
	else:
		mlines = (line.split() for line in open(mfile) if not line.startswith('#'))
	#mlines = (line.split() for line in open(args[0]) if not line.startswith('#'))
	for tok in mlines:
		chr = tok[args.mchr]
		if chr.startswith('chr'):
			chr = chr[3:]
		if not chr in mblocks:
			mblocks[chr] = []
		mblocks[chr].append((int(tok[mpos[0]]), 1))
		mblocks[chr].append((int(tok[mpos[1]]) + 1, -1))

# construct flattened and overlap masks
info('Constructing flattened and overlap masks')
fblocks = {}
oblocks = {}
for chr in mblocks:
#	print(chr)
	mblocks[chr].sort()
	fblocks[chr] = [(0, 0)]
	oblocks[chr] = [(0, 0)]
	total = 0
	for block in mblocks[chr]:
		if total == 0: 
			fblocks[chr].append((block[0], 1))
		if total == 1 and block[1] > 0: 
			oblocks[chr].append((block[0], 1))
		total += block[1]
		if total == 0: 
			fblocks[chr].append((block[0], 0))
		if total == 1 and block[1] < 0: 
			oblocks[chr].append((block[0], 0))
#	mblocks[chr]
#		block[1] = int(total > 0)
#	print(mblocks[chr][:10])
del mblocks
#print(fblocks['1'][:20])
#print(oblocks['1'][:20])

if args.info:
	total = 0
	for chr in fblocks:
		blocks = fblocks[chr]
		for x in zip(blocks[1::2], blocks[2::2]):
			total += x[1][0] - x[0][0]
	print('total masked = %d' % total)
	total = 0
	for chr in oblocks:
		blocks = oblocks[chr]
		for x in zip(blocks[1::2], blocks[2::2]):
			total += x[1][0] - x[0][0]
	print('overlap = %d' % total)

if args.ovlap:
	for chr in oblocks:
		blocks = oblocks[chr]
		for x in zip(blocks[1::2], blocks[2::2]):
			print('\t'.join([chr, str(x[0][0]), str(x[1][0] - 1)]))

if args.flatten:
	for chr in oblocks:
		blocks = fblocks[chr]
		for x in zip(blocks[1::2], blocks[2::2]):
			print('\t'.join([chr, str(x[0][0]), str(x[1][0] - 1)]))

if args.TARGET_FILE == '-':
	targetf = sys.stdin
elif args.TARGET_FILE:
	targetf = open(args.TARGET_FILE)
else:
	sys.exit()

nfilt = 0
ntot = 0
sitelines = (line.split() for line in targetf)
for l in range(headerlines):
	sys.stdout.write('\t'.join(sitelines.next())  + '\n')
for tok in sitelines:
	if tok[0].startswith('#'):
		sys.stdout.write('\t'.join(tok) + '\n')
		continue
	ntot += 1
	chr = tok[args.tchr]
	if chr.startswith('chr'):
		chr = chr[3:]
	pos = (int(tok[args.tpos]), 0)
#	print([chr, pos, fblocks[chr][bisect(fblocks[chr], pos) - 1]])
	ib = bisect(fblocks[chr], pos)
	if chr in fblocks and fblocks[chr][ib - 1][1]:
		nfilt += 1
		debug('filtering: %s:%d in %s:%d-%d' % (chr, pos[0], chr, fblocks[chr][ib - 1][0], fblocks[chr][ib][0]))
	else:
		sys.stdout.write('\t'.join(tok) + '\n')

info('removed %d of %d sites' % (nfilt, ntot))

