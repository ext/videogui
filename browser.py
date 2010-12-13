import cherrypy
import template
import os
from item import Item

class Browser(object):
    @cherrypy.expose
    def index(self):
        raise cherrypy.InternalRedirect('/browser/list')
    
    @cherrypy.expose
    @template.output('view.html')
    def list(self, *path):
        root = cherrypy.request.app.config['video']['path']
        fullpath = os.path.join(root, *path)
        
        # list all files and directories
        try:
            content = os.listdir(fullpath)
        except OSError:
            traceback.print_exc()
            return 'No such file or directory: %s' % os.path.join('/', *path)
        
        # want to include a '..' back link
        if len(path) > 0:
            content.insert(0, '..')
        
        # create wrappers for each object
        item = [Item.create(root, os.path.join(path + (x,)), x) for x in content]

        # sort
        item.sort(cmp=Item.compare)
        
        return template.render(path=os.path.join('/', *path), item=item)
        
    @cherrypy.expose
    @template.output('info.html')
    def details(self, *path):
        root = cherrypy.request.app.config['video']['path']
        fullpath = os.path.join(root, *path)
        
        return template.render(path=os.path.join('/', *path))
