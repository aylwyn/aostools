# Aylwyn Scally 2014

import sys
import subprocess
import glob
import os
import os.path
import re
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


def atoi(text):
	if text.isdigit():
		return(int(text))
	else:
		return(text)

def natural_key(text):
	'''usage: chrnames.sort(key=natural_key). http://nedbatchelder.com/blog/200712/human_sorting.html '''
	return([ atoi(c) for c in re.split('(\d+)', text) ])


def subcall(cmd, sim, dir = '', wait = False, timeout = 0, outfile = '', pipe = False, memlim = 0):
	import time, signal

#	debug(sim)
#	if sim > 1:
	if sim:
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

def fnum(num, sf = 0):
	"""Round num to sf sig figs and format compactly; arbitrary precision if sf = 0"""

	s = []
	nf = 0
	ppos = -1
	for x in str(num):
#		print((x, s))
		if x == '.':
			ppos = len(s)
			continue
		if nf == 0 and ppos < 0 and x == '0':
			continue
		s.append(x)
		if x != '-' and (x != '0' or nf > 0):
			nf += 1
		if ppos >= 0 and sf > 0 and nf > sf:
			if int(s[-1]) >= 5:
				s[-2] = str(int(s[-2]) + 1)
			s = s[:-1]
			break
	if len(s) == 0:
		s = ['0']
	if ppos >= 0:
		s.insert(ppos, '.')
		if s[0] == '.':
			s.insert(0, '0')
		return(''.join(s).rstrip('0').rstrip('.'))
	else:
		return(''.join(s))

