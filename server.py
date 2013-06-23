import cherrypy
import sqlite3
import os.path

rssToolDir = "/Users/karlli/Desktop/mm/"

class OnePage(object):
    def index(self):
        return "one page!"
    index.exposed = True


class ListPosts(object):

    def entry(self, id):
        feedDb = sqlite3.connect(rssToolDir+'feed.db')
        dbc = feedDb.cursor()
        i = (id,)
        posts = dbc.execute('SELECT * FROM posts WHERE id=?', i).fetchone()
        feedDb.close()
        return posts[1]+"</p>"+posts[5]

    def index(self):
        feedDb = sqlite3.connect(rssToolDir+'feed.db')
        dbc = feedDb.cursor()
        posts = dbc.execute('SELECT * FROM posts ORDER BY id').fetchall()
        postList = ""
        for post in posts:
            postList  = postList+"<a href='entry/"+str(post[0])+"'>"+post[1]+"</a><p>"
        feedDb.close()
        return postList

    def default(self, attr='abc'):
        return "Page not Found!"

    
    index.exposed = True
    entry.exposed = True
    default.exposed = True

conf = {'/entry/images': {'tools.staticdir.on': True,
        'tools.staticdir.dir': rssToolDir+'images'}}

cherrypy.quickstart(ListPosts(), '/', config=conf)