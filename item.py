import os
import re
import urllib

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

	return '%d%s' % (round(size), s)

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
	def __init__(self, root, path, base):
		self._root = root
		self._path = os.path.join(*path)
		self._base = base
		self._fullpath = os.path.join(root, *path)

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
			return natcasecmp(a._base, b._base)

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
		return natcasecmp(a._base, b._base)

class Folder(Item):
	def image(self):
		return 'folder.png'

	def __str__(self):
		tpath = trunc(self._base, size=35)
		return '<a href="/view/{url}">{name}</a>{padding}     - '.format(
			url=urllib.quote(self._path), name=tpath, padding=' '*(35-len(tpath)))

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
		tpath = trunc(self._base, size=35)
		fields = {
			'url': urllib.quote(self._path),
			'name': tpath,
			'padding': ' '*(35-len(tpath)),
			'size': format_size(self._size)
		}

		if not (self.is_video() or self.is_playlist()):
			return '{name}{padding} {size:>5}'.format(**fields)

		actions = File.action_menu.format(**fields)
		return '<a href="/info/{url}">{name}</a>{padding} {size:>5} {actions}'.format(actions=actions, **fields)
			

class Unknown(Item):
	def image(self):
		return 'page_white.png'

	def __str__(self):
		return trunc(self._path)
