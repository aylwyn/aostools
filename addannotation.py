#!/usr/bin/env python
# Aylwyn Scally 2012

import sys
import getopt
#import os
import os.path
import logging
import gzip
from logging import error, warning, info, debug, critical

from bisect import bisect

sim = 0
loglevel = logging.WARNING
#os.umask(0002)

mchrcol = 0
mposcol = [1,2]
schrcol = 0
sposcol = [1]
mhdr = [0,0]
mask = False
label = False
mlabcol = 0
annotitle = ''

def usage():
	sys.stderr.write('usage: %s annot_file [sites_file] [-s sites_file_chr_col,pos_col[,pos2_col]] [-a annot_file_chr_col,pos1_col,pos2_col] [-l label_col] [-m] [-h annot_hdr_lines,sites_hdr_lines] [-t col_title]\n' % (os.path.basename(sys.argv[0])))

try:
	opts, args = getopt.gnu_getopt(sys.argv[1:], 'a:ch:l:ms:t:v', ['ucsc'])
except getopt.GetoptError:
	usage()
	sys.exit(2)
for (oflag, oarg) in opts:
	if oflag == '-h':
		mhdr = [int(x) for x in oarg.split(',')]
	if oflag == '-s':
#		schr = int(oarg.split(',')[0]) - 1
#		spos = int(oarg.split(',')[1]) - 1
		scol = [int(x) - 1 for x in oarg.split(',')]
		schrcol = scol[0]
		sposcol = scol[1:]
	if oflag == '-v':
		loglevel = logging.INFO
	if oflag == '--debug':
		loglevel = logging.DEBUG
	if oflag == '-a':
		mchrcol = int(oarg.split(',')[0]) - 1
		mposcol = [int(x) - 1 for x in oarg.split(',')[1:3]]
	if oflag == '-l':
		label = True
		mlabcol = int(oarg) - 1
	if oflag == '-m':
		mask = True
	if oflag == '-t':
		annotitle = oarg

logging.basicConfig(format = '%(module)s:%(lineno)d:%(levelname)s: %(message)s', level = loglevel)

if len(args) < 1:
	usage()
	sys.exit(2)

(pointwise, ranged) = (1,2)
annot_mode = len(sposcol)

# first read annotation regions
mblocks = {}
if args[0].endswith('.gz'):
	mlines = (line.split() for line in gzip.open(args[0]) if not line.startswith('#'))
else:
	mlines = (line.split() for line in open(args[0]) if not line.startswith('#'))
hc = mhdr[0]
for tok in mlines:
	if hc > 0: #TODO: get annotitle from here
		hc -= 1
		continue
	chr = tok[mchrcol]
	if chr.startswith('chr'):
		chr = chr[3:]
	if not chr in mblocks:
		mblocks[chr] = []
	if mlabcol >= 0:
		blocklab = tok[mlabcol]
	else:
		blocklab = chr + ':' + tok[mposcol[0]] + '-' + tok[mposcol[1]]
	mblocks[chr].append([int(tok[mposcol[0]]), 1, blocklab])
	mblocks[chr].append([int(tok[mposcol[1]]) + 1, 0, blocklab])

# then construct mask
nblocks = {}
for chr in mblocks:
	labs = []
#	print(chr)
	mblocks[chr].sort()
	nblocks[chr] = [[0, '']]
	for block in mblocks[chr]:
#		print(block)
		if block[1]:
			if block[2] in labs:
				warning('repeated annotation item %s' % block[2])
			labs.append(block[2])
		else:
			labs.remove(block[2])
#		print(labs)
		nblocks[chr].append([block[0], ','.join(labs)])
#	mblocks[chr]
#		block[1] = int(total > 0)
#	print(mblocks[chr][:10])
del mblocks
#print(nblocks['3'][:20])

if len(args) < 2:
	sitesfile = sys.stdin
else:
	sitesfile = open(args[1])

if annotitle:
	annocols = ['dist']
	if label:
		annocols.append('name')
	colhdrs = '\t'.join([annotitle + '_' + x for x in annocols])

nfilt = 0
ntot = 0
hc = mhdr[1]
#sitelines = (line.split() for line in sitesfile)
pos = [0, '']
for line in sitesfile:
	if hc > 0:
		if annotitle and hc == 1: # assume last header line is to be kept
			sys.stdout.write(line.strip())
			sys.stdout.write('\t' + colhdrs + '\n')
		hc -= 1
		continue
	if line[0].startswith('#'):
		continue
	tok = line.split()
	ntot += 1
	chr = tok[schrcol]
	if chr.startswith('chr'):
		chr = chr[3:]
	if not chr in nblocks:
		continue

	if annot_mode == pointwise: # annotations at single positions
		pos[0] = int(tok[sposcol[0]])
		iannot = bisect(nblocks[chr], pos)
#		print([chr, pos, iannot, nblocks[chr][iannot - 1], nblocks[chr][iannot]])
		nlab = nblocks[chr][iannot - 1][1]
		if chr in nblocks and nblocks[chr][iannot - 1][1]:
			dist = 0
		elif mask: # output mask column (0 = overlapping, 1 = not overlapping)
			dist = 1
		else:
			udist = nblocks[chr][iannot - 1][0] - pos[0]
			dist = udist
			nlab = nblocks[chr][iannot - 2][1]
			if iannot < len(nblocks[chr]): # if there is a downstream feature
				ddist = nblocks[chr][iannot][0] - pos[0]
				if ddist + udist < 0 or iannot == 1: # if downstream feature is closer or at start of chr
					dist = ddist
					nlab = nblocks[chr][iannot][1]
		sys.stdout.write('\t'.join(tok + [str(dist)]))
		if label:
			sys.stdout.write('\t' + nlab)
		sys.stdout.write('\n')
	if annot_mode == ranged: # annotations on ranges (all features overlapping range)
		spos = [int(tok[x]) for x in sposcol]
		mid = (spos[0] + spos[1]) / 2
		iannot = bisect(nblocks[chr], [spos[0], ''])
		labset = set([])
		if nblocks[chr][iannot - 1][1]:
			labset.update(nblocks[chr][iannot - 1][1].split(','))
		else:
			udist = nblocks[chr][iannot - 1][0] - mid
			ulab = nblocks[chr][iannot - 2][1]
			ddist = 0
#		print([chr, spos, iannot, labset, nblocks[chr][iannot - 1], nblocks[chr][iannot]])
		for block in nblocks[chr][iannot:]:
			ddist = block[0] - mid
			dlab = block[1]
			if block[0] > spos[1]:
				break
			if dlab:
				labset.update(dlab.split(','))
#			print([chr, spos, iannot, labset, block])
		if not labset:
			(dist, nlab) = (udist, ulab)
			if ddist and ddist + udist < 0 or iannot == 1: # if downstream feature is closer or at start of chr
				(dist, nlab) = (ddist, dlab)
		else:
			(dist, nlab) = (0, ','.join(list(labset)))

		sys.stdout.write('\t'.join(tok + [str(dist)]))
		if label:
			sys.stdout.write('\t' + nlab)
		sys.stdout.write('\n')

#info('removed %d of %d sites' % (nfilt, ntot))
