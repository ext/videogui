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
            traceback.print_exc()
            return traceback.format_exc()
    return wrapper
    
class Player:
	def __init__(self):
		self._engines = {
			'mplayer': self._mplayer,
			'vlc': self._cvlc
			}

		self._proc = pymplb.MPlayer(fs=True, env={'DISPLAY': ':0', 'TERM': 'xterm', 'HOME': os.environ['HOME']})

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
	def loadfile(self, *url):
            print 'loadfile', url
            self._loadfile_int(url)

        @cherrypy.expose
        @catch
        def queue(self, *url):
            self._loadfile_int(url, append=1)

        def _loadfile_int(self, url, append=0):
            root = cherrypy.request.app.config['video']['path']
            fullpath = os.path.join(root, *url)

            if os.path.splitext(fullpath)[1].lower() == '.playlist':
                with open(fullpath, 'r') as fp:
                    playlist = fp.readlines()
                    
                    for item in playlist:
                        item_url = url[:-1] + (item[:-1],)
                        self._loadfile_int(item_url, append=1)
                
                return

            print 'proc::loadfile', fullpath, append
            self._proc.loadfile('"' + fullpath + '"', append)

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
            pass

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
