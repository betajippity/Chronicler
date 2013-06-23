import json
import urllib
import os
from HTMLParser import HTMLParser
import time
import sqlite3
from datetime import datetime

class imgParse(HTMLParser):
    imgLinks = []
    def handle_starttag(self, tag, attrs):
        if tag=="img":
            self.imgLinks.append(dict(attrs)["src"])
    def clear(self):
    	self.imgLinks = []


rssToolDir = "/Users/karlli/Desktop/mm/"

def grJsonToDb(feedJsonFile, feedDb):
	#load Google Reader feed JSON file
	jd = open(feedJsonFile).read()
	data = json.loads(jd)
	i = 0
	#setup images dir
	if os.path.exists(rssToolDir+'images') == False:
		os.makedirs(rssToolDir+'images')
	#setup sqlite db for feed
	dbc = feedDb.cursor()
	dbc.execute('''CREATE TABLE IF NOT EXISTS posts ("id" INTEGER PRIMARY KEY  NOT NULL , "title" TEXT, "url" TEXT, "published" DATETIME, "updated" DATETIME, "content" TEXT)''')
	feedDb.commit()
	#loop them entries
	for entry in reversed(data["items"]):
		print "Scraping post "+str(i)+" of "+str(len(data["items"])-1)+": "+entry["title"]
		id = entry["published"]
		post = ""
		if entry.has_key("content"):
			post=entry["content"]["content"]
		elif entry.has_key("summary"):
			post=entry["summary"]["content"]
		else:
			print "Error: no content in feed"
			return
		post = urllib.unquote(post)
		#get image URLs
		h=imgParse()
		h.clear()
		h.feed(post)
		imageLinks = h.imgLinks
		#download images, rename, and replace image URLs in posts
		j = 0
		for image in imageLinks:
			imagequoted = image
			image = urllib.unquote(image)
			targetfile = image.rpartition('/')[2]
			targetfile = str(j)
			try:
				urllib.urlretrieve(image, rssToolDir+"images/"+str(id)+'_'+targetfile)
			except IOError:
				print "Delaying for server to catch up..."
				time.sleep(5)
				try:
					urllib.urlretrieve(image, rssToolDir+"images/"+str(id)+'_'+targetfile)
				except IOError:
					print "Image download failed, skipping..."
			post = post.replace('src="'+str(imagequoted), urllib.unquote('src="images/'+str(id)+'_'+targetfile))
			post = post.replace("src="+str(imagequoted), urllib.unquote("src='images/"+str(id)+'_'+targetfile))
			j = j+1
		#package post data into a row for db
		publishedTime = datetime.fromtimestamp(entry["published"])
		updatedTime = datetime.fromtimestamp(entry["updated"])
		title = entry["title"]
		url = entry["alternate"][0]["href"]
		postQuery = (id, title, url, publishedTime, updatedTime, post)
		#check if post already exists in db and insert if it does not
		selectedRow = dbc.execute('SELECT * FROM posts WHERE id=?', (id,)).fetchone()
		if selectedRow == None:
			dbc.execute('INSERT INTO posts VALUES (?,?,?,?,?,?)', postQuery)
			feedDb.commit()
		else:
			print "Warning: Post with ID "+str(id)+" already exists in db."
		i = i+1
	#close sqlite db
	feedDb.close()


dbconn = sqlite3.connect(rssToolDir+'feed.db')
grJsonToDb("/Users/karlli/Desktop/mm/feed.json", dbconn)