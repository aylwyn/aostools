#!/software/bin/python
# Aylwyn Scally 2009

import sys
import subprocess
import glob
import os
import os.path
import logging
from logging import error, warning, info, debug, critical

def fwrite(name, data, mode = 'w'):
	fname = open(name, mode)
	if type(data) is str:
		data = [data]
	if len(data) == 1:
		fname.writelines(data)
	else:
		fname.writelines('\n'.join(data))
	fname.write('\n')
	fname.close()

def jobstatus(bout):
	if not os.path.exists(bout):
		info('%s not found' % bout)
		return((-2, 'absent'))
	repstat = (-1, 'incomplete')
	for line in open(bout):
		if line.startswith('Subject: Job'):
			jobstat = line.split()[-1]
			if jobstat == 'Done':
				repstat = (0, jobstat)
			else:
				repstat = (1, jobstat)
#				info('job status %s in %s' % (jobstat, bout))
				break
	return(repstat)

def jobdone(bout, firstonly = False):
	if not os.path.exists(bout):
		error('%s not found' % bout)
		return(False)
	repstat = -1
	for line in open(bout):
		if line.startswith('Subject: Job'):
			jobstat = line.split()[-1]
			if jobstat == 'Done':
				repstat = 1
			else:
				repstat = 0
				info('job status %s in %s' % (jobstat, bout))
				break
			if firstonly:
				break
	if repstat < 0:
		info('unable to determine job status in %s' % bout)
	return(repstat == 1)


def VmB(pid, VmKey):
	scale = {'kB': 1024, 'mB': 1024*1024, 'KB': 1024, 'MB': 1024*1024}
	proc_status = '/proc/%d/status' % pid
	try: # get the /proc/<pid>/status pseudo file
		v = [v for v in open(proc_status).readlines() if v.startswith(VmKey)]
		if len(v) == 1:
			t = v[0].split()  # e.g. 'VmRSS:  9999  kB'
			if len(t) == 3:
				return int(t[1]) * scale.get(t[2], 0) # convert Vm value to bytes
	except:
		warning('unable to query %s in %s' % (VmKey, proc_status))
		pass
	return 0
 
def dirglob(pattern):
	return(filter(os.path.isdir, glob.glob(pattern)))


def subcall(cmd, sim, dir = '', wait = False, timeout = 0, outfile = '', pipe = False, memlim = 0):
	import time, signal

#	debug(sim)
	if sim > 1:
		if dir:
			print('SIM: in %s:\n\t%s' % (dir, cmd))
		else:
			print('SIM: ' + cmd)
	elif not sim:
		try:
			if outfile:
				outf = open(outfile, 'a')
				p = subprocess.Popen(cmd, shell = True, stdout = outf, stderr = outf)
			elif pipe:
				p = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE)
			else:
				p = subprocess.Popen(cmd, shell = True)
			if wait:
				if timeout or memlim:
					start = time.time()
					lastres = start
					while p.poll() is None:
						time.sleep(0.1)
						now = time.time()
						if timeout and (now - start) > timeout:
							os.kill(p.pid, signal.SIGKILL)
							os.waitpid(-1, os.WNOHANG)
							warning('timeout on %s; killed' % cmd)
							break
#							return None
						if memlim and (now - lastres) > 1:
							memused = VmB(p.pid, 'VmRSS')
#							memused = VmB(p.pid, 'VmSize')
#							debug(memused)
							if memused > memlim:
								os.kill(p.pid, signal.SIGKILL)
								os.waitpid(-1, os.WNOHANG)
								warning('memory limit exceeded on %s; killed' % cmd)
								break
#								return None
							lastres = now
				else:
					p.wait()
				return p.returncode
			else:
				return(p)
		except:#(OSError, KeyboardInterrupt):
			error('subcall failed: %s' % cmd)
			raise
#			return None


def configlines(configfile):
	tagpairs = (line.split(':', 1) for line in open(configfile) if line.strip() and not line.startswith('#'))
	for tag, cont in tagpairs:
		yield (tag.strip(), cont.strip())

#######################################################

class AlignmentDir(object):
	tmpdir = 'tmp'
	levels = ['strain', 'indiv', 'lib', 'lane']

	def __init__(self, path, techlevel = False):
		self.path = os.path.abspath(path)
		if techlevel:
			self.levels = ['strain', 'indiv', 'tech', 'lib', 'lane']

	def subdirs(self, dir = '*', levelname = '', dirroot = 'strain'):
		dlevel = self.levels.index(dirroot)
		dcomps = dir.split(os.sep)
		if levelname:
			level = self.levels.index(levelname) + 1
		else:
			level = len(dcomps)
		comps = ['*'] * level
		if level < len(dcomps):
			error('%s below %s level in %s' % (dir, levelname, self.path))
			return([])
		comps[dlevel:(dlevel + len(dcomps))] = dcomps[:]
		debug(comps)
		curdir = os.path.abspath('.')
		os.chdir(self.path)
		matches = dirglob(os.path.join(*comps))
		matches = filter(lambda x: not os.path.basename(x) == self.tmpdir, matches)
		os.chdir(curdir)
		if not matches:
			error('no matches for %s in %s' % (os.path.join(*comps), self.path))
		return(matches)


class DataDir(AlignmentDir):
	def __init__(self, path):
		AlignmentDir.__init__(self, path)
		self.name = os.path.basename(self.path)
		if not os.path.exists(self.path):
			error('%s not found' % self.path)

class MapDir(AlignmentDir):
	mapname = 'aln'

	def __init__(self, path, ref = ''):
		AlignmentDir.__init__(self, path)
		self.name = os.path.basename(self.path)
		self.datadir = os.path.normpath(os.path.join(self.path, '../DATA'))
		if os.path.exists(self.path):
			self.fa = os.readlink(os.path.join(self.path, 'ref.fa'))
			self.check()
		elif ref:
			self.fa = ref

	def create(self):
		os.mkdir(self.path)
		os.symlink(self.fa, os.path.join(self.path, 'ref.fa'))
#		self.fa = os.readlink(os.path.join(self.path, 'ref.fa'))
		self.check()

	def check(self):
		if not os.path.exists(self.fa):
			warning('%s not found' % self.fa)
		if not os.path.exists(self.datadir):
			info('%s not found' % self.datadir)

def relglob(pattern, dir = ''):
	curdir = os.path.abspath('.')
	if dir:
		os.chdir(dir)
	rlist = glob.glob(pattern)
	os.chdir(curdir)
	return(rlist)

def relpath(path, dir = '.'):
	"""Returns path relative to dir."""

	apath = os.path.abspath(os.path.normpath(path))
	adir = os.path.abspath(os.path.normpath(dir))
	if apath == adir:
		return(os.curdir)

	commonpath = os.path.commonprefix((apath, adir))
	uniqpath = adir[len(commonpath):]

	if len(uniqpath) == 0:
		return(path)

	if uniqpath.startswith(os.sep):
		uniqpath = uniqpath[1:]
	lenuniq = len(uniqpath.split(os.sep))
	return os.path.normpath(os.path.join(os.sep.join(lenuniq * [os.pardir]), apath[len(commonpath):]))
