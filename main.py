import cherrypy
import sqlite3
import os
import template
import urllib
import subprocess
import pymplb

def connect(*args):
        cherrypy.thread_data.db = sqlite3.connect('site.db')
        cherrypy.thread_data.db.row_factory = sqlite3.Row
        cherrypy.thread_data.db.cursor().execute('PRAGMA foreign_keys = ON')

def get_path():
	return cherrypy.request.app.config['video']['path']

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

	print size
	return '%d%s' % (round(size), s)
		
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
		print 'fullpath', fullpath

		if base == '..':
			return Folder(root, path, '..')
		elif os.path.isdir(fullpath):
			return Folder(root, path, base)
		elif os.path.isfile(fullpath):
			return File(root, path, base)
		else:
			return Unknown(root, path, base)

class Folder(Item):
	def image(self):
		return 'folder.png'

	def __str__(self):
		tpath = trunc(self._base, size=35)
		return '<a href="/view/{url}">{name}</a>{padding}     - '.format(
			url=urllib.quote(self._path), name=tpath, padding=' '*(35-len(tpath)))

class File(Item):
	def __init__(self, root, path, base):
		Item.__init__(self, root, path, base)
			
		statinfo = os.stat(self._fullpath)
		self._size = statinfo.st_size


	def image(self):
		return 'film.png'

	def __str__(self):
		tpath = trunc(self._base, size=35)
		return '<a href="/info/{url}">{name}</a>{padding} {size:>5} [<a href="/play/{url}">play</a>]'.format(
			url=urllib.quote(self._path), name=tpath, padding=' '*(35-len(tpath)), size=format_size(self._size))

class Unknown(Item):
	def image(self):
		return 'page_white.png'

	def __str__(self):
		return trunc(self._path)

class Player:
	STOPPED = 0
	RUNNING = 1

	def __init__(self):
		self._engines = {
			'mplayer': self._mplayer,
			'vlc': self._cvlc
			}

		self._status = Player.STOPPED
		self._proc = pymplb.MPlayer(fs=True, env={'DISPLAY': ':0', 'TERM': 'xterm'})

	def status(self):
		#if self._proc != None:
		#	if self._proc.poll():
		#		self._proc = None

		return self._status

	def filename(self):
		return self._proc.p_filename

	def position(self):
		return self._proc.p_time_pos

	def length(self):
		return self._proc.p_length

	def play(self, target, engine, *args, **kwargs):
		#if self._status != Player.STOPPED:
		#	raise RuntimeError('Player already playing')

		#self._filename = target
		e = self._engines[engine]
		e(target, *args, **kwargs)

	def stop(self):
		self._proc.stop()

	def seek(self, pos, type=0):
		self._proc.seek(pos, type)

	def _mplayer(self, target, *args, **kwargs):
		args = list(args)
		for k,v in kwargs.items():
			args.append(k)
			args.append(v)

		self._proc.loadfile(target)
		self._status = Player.RUNNING

	def _cvlc(self, target, *args, **kwargs):
		pass
	

cherrypy.engine.subscribe('start_thread', connect)
player = Player()

class Root(object):
        @cherrypy.expose
        def index(self):
                raise cherrypy.InternalRedirect('/view')

	@cherrypy.expose
	@template.output('view.html')
	def view(self, *path):
		root = get_path()
		fullpath = os.path.join(root, *path)

		try:
			content = os.listdir(fullpath)
		except OSError:
			return 'No such file or directory: %s' % os.path.join('/', *path)

		# want to include a '..' back link
		if len(path) > 0:
			content.insert(0, '..')

		item = [Item.create(root, os.path.join(path + (x,)), x) for x in content]

		return template.render(path=os.path.join('/', *path), item=item)

	@cherrypy.expose
	def play(self, *path):
		global player
		root = get_path()
		fullpath = os.path.join(root, *path)

		player.play(fullpath, 'mplayer', '-fs', '-really-quiet', ao='alsa')
		raise cherrypy.HTTPRedirect('/player')

	@cherrypy.expose
	@template.output('player.html')
	def player(self, action='status', *args):
		global player

		if action == 'stop':
			player.stop()
			raise cherrypy.HTTPRedirect('/view')

		if action == 'seek':
			player.seek(float(args[0]))
			raise cherrypy.HTTPRedirect('/player')

		return template.render(player=player)
		
application = cherrypy.tree.mount(Root(), '/', config='site.conf')
application.config.update({
        '/': {
                'tools.staticdir.root': os.path.dirname(os.path.abspath(__file__)),
                'tools.encode.on':True,
                'tools.encode.encoding':'utf8',
        }
})

cherrypy.config.update({'sessionFilter.on': True}) 

if __name__ == '__main__':
        cherrypy.config.update('site.conf')

        if hasattr(cherrypy.engine, 'block'):
            # 3.1 syntax
            cherrypy.engine.start()
            cherrypy.engine.block()
        else:
            # 3.0 syntax
            cherrypy.server.quickstart()
            cherrypy.engine.start()
