import pymplb
import cherrypy
import json
import template
import traceback
import os

def catch(func):
	""" catches all exceptions and returns them as a string. """
	def wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except:
			return traceback.format_exc()
	return wrapper

class Player:
	def __init__(self):
		self._engines = {
			'mplayer': self._mplayer,
			'vlc': self._cvlc
			}

		self._proc = pymplb.MPlayer(fs=True, env={'DISPLAY': ':0', 'TERM': 'xterm'})

	def is_playing(self):
		return self._proc.p_filename != None

	def filename(self):
		return self._proc.p_filename

	def position(self):
		return self._proc.p_time_pos

	def length(self):
		return self._proc.p_length

        @cherrypy.expose
        @catch
	def loadfile(self, *path):
		e = self._engines['mplayer']
		root = cherrypy.request.app.config['video']['path']
		fullpath = os.path.join(root, *path)

		e(fullpath, '-fs', '-really-quiet', ao='alsa')

	@cherrypy.expose
	@template.output('player.html')
	def index(self):
		return template.render()

	@cherrypy.expose
	@catch
	def stop(self):
		self._proc.stop()

	@cherrypy.expose
	@catch
	def seek(self, pos, type=0):
		self._proc.seek(float(pos), type)

	def _mplayer(self, target, *args, **kwargs):
		args = list(args)
		for k,v in kwargs.items():
			args.append(k)
			args.append(v)

                print 'playing', target
		self._proc.loadfile(target)

	def _cvlc(self, target, *args, **kwargs):
		pass

	@cherrypy.expose
	def player_progress(self):
            if not self.is_playing():
                return json.dumps({'playing': False})

            return json.dumps({
                    'playing': True,
                    'filename': self.filename(),
                    'position': self.position(),
                    'length': self.length()
                    })
