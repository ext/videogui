#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import urllib
import cherrypy
import subprocess

def trunc(string, size=35, suffix='..'):
	""" Truncates a string to size, appending a suffix. """
	msize = size - len(suffix)

	if len(string) > size:
		return '%.*s%s' % (msize, string, suffix)
	
	return string

def format_size(size):
	suffix = ['K', 'M', 'G', 'T']
	s = ''

	size = float(size)
	while size > 1024.0:
		s = suffix.pop(0)
		size /= 1024.0

	return '%2.1f%s' % (size, s)

# natural sorting from http://code.activestate.com/recipes/285264-natural-string-sorting/
def try_int(s):
        "Convert to integer if possible."
        try: return int(s)
        except: return s
def natsort_key(s):
        "Used internally to get a tuple by which s is sorted."
        return map(try_int, re.findall(r'(\d+|\D+)', s))
def natcmp(a, b):
        "Natural string comparison, case sensitive."
        return cmp(natsort_key(a), natsort_key(b))
def natcasecmp(a, b):
        "Natural string comparison, ignores case."
        return natcmp(a.lower(), b.lower())


class Item:
	width = 65

	def __init__(self, root, path, base):
		self._root = root
		self._path = os.path.join(*path)
		self._base = base
		self._fullpath = os.path.join(root, *path)
		self._title = self._base

	def image(self):
		raise NotImplementedError

	@staticmethod
	def create(root, path, base):
		fullpath = os.path.join(root, *path)

		if base == '..':
			return Folder(root, path, '..')
		elif os.path.isdir(fullpath):
			return Folder(root, path, base)
		elif os.path.isfile(fullpath):
			return File(root, path, base)
		else:
			return Unknown(root, path, base)

	@staticmethod
	def compare(a, b):
		# for instances of the same type, compare the basename
		if a.__class__ == b.__class__:
			return natcasecmp(a._title, b._title)

		# for instances of different classes, prioritize in this order:
		# 1. folder
		# 2. files
		# 3. unknown
		p = [Folder, File, Unknown]

		for t in p:
			if isinstance(a, t):
				return -1
			if isinstance(b, t):
				return 1

		# now if we reach this we probably have an invalid item in the list
		# but lets try to compare it anyway
		return natcasecmp(a._title, b._title)

class Folder(Item):
	def image(self):
		return 'folder.png'

	def __str__(self):
		tpath = trunc(self._base, size=Item.width)
		return '<a href="/browser/list/{url}">{name}</a>{padding}     - '.format(
			url=urllib.quote(self._path.encode('utf-8')), name=tpath, padding=' '*(Item.width-len(tpath)))

class File(Item):
	# known video extensions
	video_extensions = ['avi', 'mkv', 'wmv', 'mov', 'mp4', 'm4v', 'mpg', 'mpeg', 'img', 'flv']

	# playlist extensions
	playlist_extensions = ['playlist']

	# show for video files only
	action_menu = '[<a href="javascript:loadfile(\'{url}\');" target="player">play</a>]'

	def __init__(self, root, path, base):
		Item.__init__(self, root, path, base)
			
		statinfo = os.stat(self._fullpath)
		self._size = statinfo.st_size

		# try to detect video files
		self._ext = os.path.splitext(base)[1][1:].lower()
		self._is_video = self._ext in File.video_extensions
		self._is_playlist = self._ext in File.playlist_extensions

		# query metadata
		db = cherrypy.thread_data.db.cursor()
		row = db.execute('SELECT title FROM item WHERE path = :path LIMIT 1', dict(path=self._path)).fetchone()
		if row:
			self._title = row['title']
		else:
			db.execute('INSERT INTO item (path, title) VALUES (:path, :title)', dict(path=self._path, title=self._title))
			self.rescan()
			cherrypy.thread_data.db.commit()

		self._meta = {}
		for row in db.execute('SELECT key, value FROM item_meta WHERE path = :path', dict(path=self._path)).fetchall():
			key = row['key']
			value = row['value']
			self._meta[key] = value

	def rescan(self):
		meta = []

		if self.is_video():
			meta += self._retrieve_metadata()

		cherrypy.thread_data.db.executemany('REPLACE INTO item_meta (path, key, value) VALUES (?, ?, ?)', meta)
		cherrypy.thread_data.db.commit()
		
	
	def _retrieve_metadata(self):
		proc = subprocess.Popen(['midentify', self._fullpath], stdout=subprocess.PIPE)
		stdout = proc.communicate()[0]

		needed_keys = [re.compile(x) for x in [
			'ID_VIDEO_FORMAT',
			'ID_AUDIO_FORMAT',
			'ID_LENGTH',
			'ID_SID_[0-9]+_LANG',
			'ID_VIDEO_WIDTH',
			'ID_VIDEO_HEIGHT'
		]]

		meta = []
		for line in stdout.split("\n"):
			if line == '':
				continue

			[key, value] = line.split('=')

			if not any([x.match(key) for x in needed_keys]):
				continue

			meta.append((self._path, unicode(key), unicode(value, encoding='utf-8')))

		return meta

	def title(self):
		return self._title

	def set_title(self, title):
		cherrypy.thread_data.db.cursor().execute('UPDATE item SET title = :title WHERE path = :path', dict(path=self._path, title=title))
		cherrypy.thread_data.db.commit()

	def basename(self):
		return self._base

	def __getitem__(self, key):
		return self._meta[key]

	def get_meta(self, key, default=None):
		return self._meta.get(key, default)

	def size(self, format=True):
		if format:
			return format_size(self._size)
		return self._size

	def length(self, format=True):
		try:
			x = float(self._meta['ID_LENGTH'])
		except KeyError:
			return None

		if format:
			m, s = divmod(x, 60)
			h, m = divmod(m, 60)
			return '%02d:%02d:%02d' % (h, m, s)
		return x

	def video_codec(self):
		return self._meta.get('ID_VIDEO_FORMAT', None)

	def audio_codec(self):
		return self._meta.get('ID_AUDIO_FORMAT', None)

	def resolution(self, format=True):
		try:
			x = (int(self._meta['ID_VIDEO_WIDTH']),
			     int(self._meta['ID_VIDEO_HEIGHT']))
		except KeyError:
			return None

		if format:
			return '%dx%d' % x
		return x

	def is_video(self):
		return self._is_video

	def is_playlist(self):
		return self._is_playlist

	def image(self):
		if self.is_video():
			return 'film.png'
		if self.is_playlist():
			return 'film_link.png'
		
		return 'page_white.png'

	def __str__(self):
		tpath = trunc(self._title, size=Item.width)
		fields = {
			'url': urllib.quote(self._path.encode('utf-8')),
			'name': tpath,
			'padding': ' '*(Item.width-len(tpath)),
			'size': self.size(format=True)
		}

		if not (self.is_video() or self.is_playlist()):
			return '{name}{padding} {size:>5}'.format(**fields)

		actions = File.action_menu.format(**fields)
		return u'<a href="/browser/get/{url}">{name}</a>{padding} {size:>5} {actions}'.format(actions=actions, **fields)
			

class Unknown(Item):
	def image(self):
		return 'page_white.png'

	def __str__(self):
		return trunc(self._path)
