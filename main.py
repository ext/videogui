import cherrypy
import sqlite3
import os
import template
import urllib
import subprocess
import re
import traceback
from player import get_player
from browser import Browser

def connect(*args):
        cherrypy.thread_data.db = sqlite3.connect('site.db')
        cherrypy.thread_data.db.row_factory = sqlite3.Row
        cherrypy.thread_data.db.cursor().execute('PRAGMA foreign_keys = ON')

cherrypy.engine.subscribe('start_thread', connect)

class Root(object):
	player = get_player()
	browser = Browser()

        @cherrypy.expose
	@template.output('frame.html', doctype='xhtml-frameset')
        def index(self):
                return template.render()

	@cherrypy.expose
	@template.output('info.html')
	def info(self, *path):
		root = cherrypy.request.app.config['video']['path']
		fullpath = os.path.join(root, *path)

		return template.render(path=os.path.join('/', *path))
		
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
