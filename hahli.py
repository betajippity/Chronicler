import xml.etree.ElementTree as ET
import os
import sqlite3
import urllib
import urllib2
import time
import json
from HTMLParser import HTMLParser
from datetime import datetime
import hashlib
import imghdr
import feedparser
import sys

#Takes in a subs database and three strings for feed XML address, feed URL, and feed title, and adds a new feed entry to the given subs database.
def addFeedToSubsDb(subsDb, feedXML, feedURL, feedTitle):
	db = subsDb.cursor()
	if feedXML[-1]=='_':
		feedXML = feedXML[:-1]
	feedQuery = (feedXML, feedTitle, feedURL, True)
	#check if feed already exists in db and insert if it does not
	selectedRow = db.execute('SELECT * FROM feeds WHERE feedURL=?', (feedXML,)).fetchone()
	if selectedRow == None:
		db.execute('INSERT INTO feeds VALUES (?,?,?,?)', feedQuery)
		subsDb.commit()
		print "Added feed "+feedXML+" to database."
	else:
		print "Error: Feed "+feedXML+" already exists in database."

#Takes in a path to an opml file and adds contents to a subs database in the given rssToolDir directory.
def createSubsDbFromOPML(opmlFile, rssToolDir):
	#load opml
	parseTree = ET.parse(opmlFile).getroot()
	#setup sqlite db for subscriptions
	subsDb = openSubsDb(rssToolDir)
	#loop through subscriptions and add each subscription to subsDb
	for feed in parseTree[1]:
		addFeedToSubsDb(subsDb, feed.attrib['xmlUrl'], feed.attrib['htmlUrl'], feed.attrib['title'])

#Opens or creates a subs database in the current rssToolDir directory.
def openSubsDb(rssToolDir):
	#setup sqlite db for subscriptions
	subsDb = sqlite3.connect(rssToolDir+'subscriptions.db')
	dbc = subsDb.cursor()
	#check if feeds table exists and create if necessary
	dbc.execute('''CREATE TABLE IF NOT EXISTS feeds ("feedURL" TEXT PRIMARY KEY  NOT NULL ,"name" TEXT,"htmlURL" TEXT,"full" BOOL DEFAULT (1) )''')
	subsDb.commit()
	return subsDb

#Takes in feed XML address and downloads corresponding Google Reader feed archive
def downloadFeedArchiveFromGReader(feedXML, rssToolDir):
	#setup feeds dir
	if os.path.exists(rssToolDir+'feeds') == False:
		os.makedirs(rssToolDir+'feeds')
	#process URLs and filenames, make subdir for feed if necessary
	xmlfilename = feedXML.replace('http://','').replace('/','_')
	if xmlfilename[-1]=='_':
		xmlfilename = xmlfilename[:-1]
	if os.path.exists(rssToolDir+'feeds/'+xmlfilename) == False:
		os.makedirs(rssToolDir+'feeds/'+xmlfilename)
	#start by stripping any trailing /s from the feedURL, pull the archive, and then repeat with a trailing / added back.
	if feedXML[-1]=='/':
		feedXML = feedXML[:-1]
	greaderurl = "http://www.google.com/reader/api/0/stream/contents/feed/"+urllib.quote(feedXML, '')+"?n=9999&ot=0"
	#download archive for feedURL with no trailing /
	archivenumber = ""
	urlc = urllib.urlopen(greaderurl)
	if urlc.getcode()!=404:
		archive = ""
		try:
			archive = urlc.read()
			print "Downloading archive of " + feedXML + " from Google Reader API"
		except IOError:
			print "Delaying for server to catch up..."
			time.sleep(5)
			try:
				archive = urlc.read()
				print "Downloading archive of " + feedXML + " from Google Reader API"
			except IOError:
				print "Feed " + feedXML + " archive could not be downloaded from Google Reader API"
		file = open(rssToolDir+"feeds/"+xmlfilename+"/archive"+archivenumber+".json", 'w')
		file.write(archive)
		file.close()
		archivenumber = "2"
	#add / back in and download archive
	feedXML = feedXML+"/"
	greaderurl = "http://www.google.com/reader/api/0/stream/contents/feed/"+urllib.quote(feedXML, '')+"?n=9999&ot=0"
	#download archive for feedURL with trailing /
	urlc = urllib.urlopen(greaderurl)
	if urlc.getcode()!=404:
		archive = ""
		try:
			archive = urlc.read()
			print "Downloading archive of " + feedXML + " from Google Reader API"
		except IOError:
			print "Delaying for server to catch up..."
			time.sleep(5)
			try:
				archive = urlc.read()
				print "Downloading archive of " + feedXML + " from Google Reader API"
			except IOError:
				print "Feed " + feedXML + " archive could not be downloaded from Google Reader API"
		file = open(rssToolDir+"feeds/"+xmlfilename+"/archive"+archivenumber+".json", 'w')
		file.write(archive)
		file.close()

#Takes in a subs database and downloads feed archives from Google Reader API for all feeds in the database
def getAllArchives(subsDb, rssToolDir):
	db = subsDb.cursor()
	feeds = db.execute('SELECT * FROM feeds').fetchall()
	#setup feeds dir
	if os.path.exists(rssToolDir+'feeds') == False:
		os.makedirs(rssToolDir+'feeds')
	#loop over feeds and download each feed's Google Reader archive
	for feed in feeds:
		downloadFeedArchiveFromGReader(feed[0], rssToolDir)

#Class extending HTML parser to pull out images
class imgParse(HTMLParser):
    imgLinks = []
    def handle_starttag(self, tag, attrs):
    	#print attrs
        if tag=="img":
        	if dict(attrs).has_key('src'):
        		self.imgLinks.append(dict(attrs)['src'])
    def clear(self):
    	self.imgLinks = []

#Opens or creates a feed database in the current rssToolDir directory
def openFeedDb(feedXML, rssToolDir):
	#create subdir for feed if necessary
	xmlfilename = feedXML.replace('http://','').replace('/','_')
	if xmlfilename[-1]=='_':
		xmlfilename = xmlfilename[:-1]
	if os.path.exists(rssToolDir+'feeds/'+xmlfilename) == False:
		os.makedirs(rssToolDir+'feeds/'+xmlfilename)
	#setup sqlite db for subscriptions
	feedDb = sqlite3.connect(rssToolDir+'feeds/'+xmlfilename+'/feed.db')
	dbc = feedDb.cursor()
	#check if feeds table exists and create if necessary
	dbc.execute('''CREATE TABLE IF NOT EXISTS posts ("id" VARCHAR PRIMARY KEY  NOT NULL , "title" TEXT, "url" TEXT, "published" DATETIME, "updated" DATETIME, "content" TEXT)''')
	#check if images table exists and create if necessary
	dbc.execute('''CREATE TABLE IF NOT EXISTS images ("original" TEXT PRIMARY KEY  NOT NULL , "cached" TEXT)''')
	feedDb.commit()
	return feedDb

#Adds all entries in a Google Reader archive to a feed database. Optionally will download images too if cacheImages is true
def addArchiveToFeedDb(feedXML, rssToolDir, cacheImages):
	#get our feed database
	feedDb = openFeedDb(feedXML, rssToolDir)
	#get our archive json
	xmlfilename = feedXML.replace('http://','').replace('/','_')
	if xmlfilename[-1]=='_':
		xmlfilename = xmlfilename[:-1]
	if os.path.isfile(rssToolDir+"feeds/"+xmlfilename+"/archive.json") == True:
		jd = open(rssToolDir+"feeds/"+xmlfilename+"/archive.json").read()
		archiveData = json.loads(jd)
		for entry in reversed(archiveData["items"]):
			addArchiveEntryToFeedDb(feedXML, feedDb, entry, cacheImages, rssToolDir)
	if os.path.isfile(rssToolDir+"feeds/"+xmlfilename+"/archive2.json") == True:
		jd = open(rssToolDir+"feeds/"+xmlfilename+"/archive2.json").read()
		archiveData = json.loads(jd)
		for entry in reversed(archiveData["items"]):
			addArchiveEntryToFeedDb(feedXML, feedDb, entry, cacheImages, rssToolDir)
	feedDb.close()


def addArchiveEntryToFeedDb(feedXML, feedDb, archiveEntry, cacheImages, rssToolDir):
	return addEntryToFeedDb(feedXML, feedDb, archiveEntry, cacheImages, rssToolDir, "posts")

#Adds a Google Reader archive entry as a post to a feed database. Optionally will download images too if cacheImages is true
def addEntryToFeedDb(feedXML, feedDb, archiveEntry, cacheImages, rssToolDir, table):
	dbc = feedDb.cursor()
	post = ""
	if archiveEntry.has_key("content"):
		post=archiveEntry["content"]["content"]
	elif archiveEntry.has_key("summary"):
		post=archiveEntry["summary"]["content"]
	title = ""
	if archiveEntry.has_key("title"):
		title = HTMLParser().unescape(archiveEntry["title"])
	post = urllib.unquote(HTMLParser().unescape(post))
	url = ""
	if archiveEntry.has_key("alternate"):
		url = archiveEntry["alternate"][0]["href"]
	if title=="":
		if url=="":
			print "Warning: No title or URL!"
	#get ID for post by hashing title with date added to front
	hashstring = str(title.encode('ascii', 'ignore'))+str(url.replace('https://','http://').encode('ascii', 'ignore'))
	id = hashlib.sha224(hashstring).hexdigest()
	#check if post already exists in db and insert if it does not
	selectedRow = dbc.execute('SELECT * FROM '+table+' WHERE id=?', (id,)).fetchone()
	if selectedRow == None:
		if cacheImages==True:
			#setup images dir
			xmlfilename = feedXML.replace('http://','').replace('https://','').replace('/','_')
			if xmlfilename[-1]=='_':
				xmlfilename = xmlfilename[:-1]
			imagedir = rssToolDir+"feeds/"+xmlfilename;
			if os.path.exists(imagedir+'/images') == False:
				os.makedirs(imagedir+'/images')
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
				imageType = downloadImage(image, imagedir+"/images/"+str(id)+'_'+targetfile)
				if imageType!="NotAnImage":
					if imageType!=None:
						imageQuery = (image, str(id)+'_'+targetfile+"."+imageType)
						selectedImage = dbc.execute('SELECT * FROM images WHERE original=?', (image,)).fetchone()
						if selectedImage == None:
							dbc.execute('INSERT INTO images VALUES (?,?)', imageQuery)
						else:
							print "Warning: Image "+image+" has already been cached."
					j = j+1
		#package post data into a row for db
		publishedTime = datetime.fromtimestamp(archiveEntry["published"])
		updatedTime = datetime.fromtimestamp(archiveEntry["updated"])
		postQuery = (id, title, url, publishedTime, updatedTime, post)
		dbc.execute('INSERT INTO '+table+' VALUES (?,?,?,?,?,?)', postQuery)
		feedDb.commit()
		print "Added post with ID "+str(id)+" to db table "+table
		return 0
	else:
		i = 0
		#print "Warning: Post with ID "+str(id)+" already exists in db."
		return 1

#Downloads a given image to the given file. Returns the image type.
def downloadImage(imageURL, targetFile):
	print "Downloading " + imageURL
	safeurl = urllib2.quote(str(imageURL.encode('utf8'))).replace("%3A", ":")
	headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.77 Safari/535.7'}
	req = urllib2.Request(safeurl, headers=headers)
	urlc = None
	try:
		urlc = urllib2.urlopen(req)
	except urllib2.HTTPError as e: 
		print "Error for "+ imageURL + ":"
		print e
		return "NotAnImage"
	except urllib2.URLError as e:
		print "Error for "+ imageURL + ":"
		print e
		return "NotAnImage"
	except Exception as e:
		print "Error for "+ imageURL + ":"
		print e
		return "NotAnImage"
	imageData = urlc.read()
	imageType = imghdr.what(None, imageData)
	if imageType!=None:
		if os.path.isfile(targetFile+"."+imageType)==False:
			imageFile = open(targetFile+"."+imageType, 'w')
			imageFile.write(imageData)
			imageFile.close()
		else:
			print "Skipping "+targetFile+"."+imageType+", file already exists"
	return imageType

#Takes in a subs database and adds all feeds to feed databases and optionally downloads images
def addAllArchivesToFeedDbs(subsDb, rssToolDir, cacheImages):
	db = subsDb.cursor()
	feeds = db.execute('SELECT * FROM feeds').fetchall()
	for feed in feeds:
		#print "Adding posts from "+feed[0]+" to feed database."
		addArchiveToFeedDb(feed[0], rssToolDir, cacheImages)

#Takes in a subs database and adds all feeds to feed databases and optionally downloads images
def updateAllFeeds(subsDb, rssToolDir, cacheImages):
	db = subsDb.cursor()
	feeds = db.execute('SELECT * FROM feeds').fetchall()
	addedFeeds = []
	for feed in feeds:
		print "Adding new posts from "+feed[0]+" to feed database."
		feedDb = openFeedDb(feed[0], rssToolDir)
		updates = updateFeed(feed[0], feedDb, rssToolDir, cacheImages)
		if updates>0:
			addedFeeds.append("Added "+str(updates)+" new posts to "+feed[0])
		feedDb.close()
	print ""
	print "Update Summary: "+str(len(addedFeeds))+" feeds updated."
	for feed in addedFeeds:
		print feed
	print ""

#Takes in a subs database and checks all feed dbs for broken image entries
def checkAllFeedDbImages(subsDb, rssToolDir):
	db = subsDb.cursor()
	feeds = db.execute('SELECT * FROM feeds').fetchall()
	for feed in feeds:
		print "Checking images in feed database for "+feed[0]
		feedDb = openFeedDb(feed[0], rssToolDir)
		checkFeedDbImages(feed[0], feedDb, subsDb, rssToolDir)
		feedDb.close()

#Checks for broken image entries in feed db
def checkFeedDbImages(feedXML, feedDb, subsDb, rssToolDir):
	images = feedDb.execute('SELECT * FROM images ORDER BY rowid').fetchall()
	for image in images:
		xmlfilename = feedXML.replace('http://','').replace('/','_')
		if xmlfilename[-1]=='_':
			xmlfilename = xmlfilename[:-1]
		imagePath = rssToolDir+"feeds/"+xmlfilename+"/images/"+image[1]
		if os.path.isfile(imagePath)==False:
			target = image[1].replace(".","")
			result = downloadImage(image[0], rssToolDir+"feeds/"+xmlfilename+"/images/"+target)
			if result=="NotAnImage":
				#add broken image to broken image table for possible future re-trying
				feedDb.execute('''CREATE TABLE IF NOT EXISTS images_broken ("original" TEXT PRIMARY KEY  NOT NULL , "cached" TEXT)''')
				broken = (image[0], image[1])
				feedDb.execute('INSERT INTO images_broken VALUES (?,?)', broken)
				#remove broken entry from main image table
				updates = {"u1":image[0]}
				updatequery = "DELETE FROM images WHERE original==:u1"
				feedDb.execute(updatequery, updates)
				feedDb.commit()
				print "Removing broken entry " + image[1] + "from db"
			else:
				updates = {"u1":target+"."+result, "u2":image[0]}
				updatequery = "UPDATE images SET cached==:u1 WHERE original==:u2"
				feedDb.execute(updatequery, updates)
				feedDb.commit()
				print "Successfully fixed missing image " + target+"."+result


def checkFeedDbHTTP(feedXML, feedDb):
	posts = feedDb.execute('SELECT * FROM posts ORDER BY rowid').fetchall()
	for post in posts:
		if "https://" in post[2]:
			print post[2]
			print feedXML

def pullEntryFromReadability(apikey, url):
	apiCall = "https://www.readability.com/api/content/v1/parser?url="+url+"&token="+apikey
	confidenceCall = "https://www.readability.com/api/content/v1/confidence?url="+url
	article = json.loads(urllib.urlopen(apiCall).read())
	confidence = json.loads(urllib.urlopen(confidenceCall).read())
	print "Pulling from Readability: "+url 
	if float(confidence["confidence"])<.99:
		print "Error: article confidence is below 99% ("+url+"); Confidence: "+str(confidence["confidence"])
		return "ReadabilityFailed"
	return article

def updateFeed(feedXML, feedDb, rssToolDir, cacheImages):
	feed = feedparser.parse(feedXML)
	entries = {}
	
	if feed.bozo==1:
		print type(feed.bozo_exception)
		if type(feed.bozo_exception)==feedparser.NonXMLContentType:
			feed.bozo=0
		if type(feed.bozo_exception)==feedparser.CharacterEncodingOverride:
			feed.bozo=0

	if feed.bozo==1:
		print "Error: bad feed"
		return 0
	else:
		i = 0
		for post in feed["items"]:
			entry = {}
			entry["content"] = {}
			if post.has_key("content"):
				if post["content"][0].has_key("value"):
					entry["content"]["content"] = post["content"][0]["value"]
			elif post.has_key("summary"):
				entry["content"]["content"] = post["summary"]
			else:
				entry["content"]["content"] = ""
			entry["content"]["content"] = entry["content"]["content"].replace(" />", ">")
			entry["title"] = ""
			if post.has_key("title"):
				entry["title"] = post["title"]
			entry["updated"]=""
			if post["updated_parsed"]==None:
				entry["updated"] = time.mktime(post["published_parsed"])
			else:
				entry["updated"] = time.mktime(post["updated_parsed"])
			entry["published"] = entry["updated"]
			if(post.has_key("published_parsed")):
				entry["published"] = time.mktime(post["published_parsed"])

			alt = {}
			alt["href"] = post["link"]
			entry["alternate"] = []
			entry["alternate"].append(alt)
			#print entry["content"]["content"]
			if addArchiveEntryToFeedDb(feedXML, feedDb, entry, cacheImages, rssToolDir)==0:
				i=i+1
		print "Added " + str(i) + " new posts to feed " + feedXML
		return i

#Takes a feed database and pull full articles from Readability
def pullFeedFromReadability(feedXML, feedDb, rssToolDir, cacheImages, apikey):
	dbc = feedDb.cursor()
	dbc.execute('''CREATE TABLE IF NOT EXISTS posts_full ("id" VARCHAR PRIMARY KEY  NOT NULL , "title" TEXT, "url" TEXT, "published" DATETIME, "updated" DATETIME, "content" TEXT)''')
	posts = dbc.execute('SELECT * FROM posts').fetchall()
	for post in posts:
		query = (post[0],)
		alreadyCached = dbc.execute('SELECT * FROM posts_full WHERE id=?', query).fetchall()
		if len(alreadyCached)==0:
			postURL = post[2]
			article = pullEntryFromReadability(apikey, postURL)
			if article!="ReadabilityFailed":
				entry = {}
				entry["content"] = {}
				entry["content"]["content"] = article["content"]
				entry["title"] = post[1]
				entry["updated"] = time.mktime(datetime.strptime(post[4], '%Y-%m-%d %H:%M:%S').timetuple())
				entry["published"] = time.mktime(datetime.strptime(post[3], '%Y-%m-%d %H:%M:%S').timetuple())
				alt = {}
				alt["href"] = post[2]
				entry["alternate"] = []
				entry["alternate"].append(alt)
				addEntryToFeedDb(feedXML, feedDb, entry, cacheImages, rssToolDir, "posts_full")
			else:
				entry = {}
				entry["content"] = {}
				entry["content"]["content"] = post[5]
				entry["title"] = post[1]
				entry["updated"] = time.mktime(datetime.strptime(post[4], '%Y-%m-%d %H:%M:%S').timetuple())
				entry["published"] = time.mktime(datetime.strptime(post[3], '%Y-%m-%d %H:%M:%S').timetuple())
				alt = {}
				alt["href"] = post[2]
				entry["alternate"] = []
				entry["alternate"].append(alt)
				addEntryToFeedDb(feedXML, feedDb, entry, cacheImages, rssToolDir, "posts_full")

#Takes in a subs database and pulls all non-full feeds from Readability
def pullFeedsFromReadability(subsDb, rssToolDir, cacheImages, apikey):
	db = subsDb.cursor()
	feeds = db.execute('SELECT * FROM feeds').fetchall()
	addedFeeds = []
	for feed in feeds:
		#print "Pulling new posts from "+feed[0]+" from Readability."
		if feed[3]==0:
			feedDb = openFeedDb(feed[0], rssToolDir)
			pullFeedFromReadability(feed[0], feedDb, rssToolDir, cacheImages, apikey)
			print feed[0]

#Main method takes in settings.json file and runs according to given arguments
def main(argv):
	defaultSettingsFile = True
	settings = {}
	tasks = []
	overrides = {}
	#read args
	for arg in argv:
		flag = arg.split("=")
		if flag[0] == "settings":
			defaultSettingsFile = False
			jd = open(flag[1]).read()
			settings = json.loads(jd)
		if flag[0] == "update":
			tasks.append("update")
		if flag[0] == "addsubs":
			tasks.append("addsubs")
		if flag[0] == "checkimages":
			tasks.append("checkimages")
		if flag[0] == "readability":
			tasks.append("readability")
		if flag[0] == "readabilityapikey":
			overrides["readabilityapikey"] = flag[1]
		if flag[0] == "opml":
			overrides["opml"] = flag[1]
		if flag[0] == "rootdir":
			overrides["rootdir"] = flag[1]
		if flag[0] == "cacheimages":
			if flag[1] == True:
				overrides["cacheimages"] = True;
			else:
				overrides["cacheimages"] = False;
	#load default settings if needed
	if defaultSettingsFile==True:
		jd = open("settings.json").read()
		settings = json.loads(jd)
	#apply settings overrides
	if len(overrides)>0:
		if overrides.has_key("opml"):
			settings["opml"] = overrides["opml"]
		if overrides.has_key("rootdir"):
			settings["rootdir"] = overrides["rootdir"]
		if overrides.has_key("checkimages"):
			settings["checkimages"] = overrides["checkimages"]
		if overrides.has_key("readabilityapikey"):
			settings["readabilityapikey"] = overrides["readabilityapikey"]
	#check rootdir path
	if settings["rootdir"][:-1]!="/":
		settings["rootdir"] = settings["rootdir"]+"/"
	#run assigned tasks
	for task in tasks:
		if task == "addsubs":
			createSubsDbFromOPML(settings["opml"], settings["rootdir"])		
		if task == "update":
			subsDb = openSubsDb(settings["rootdir"])
			updateAllFeeds(subsDb, settings["rootdir"], settings["cacheimages"])
		if task == "checkimages":
			subsDb = openSubsDb(settings["rootdir"])
			checkAllFeedDbImages(subsDb, settings["rootdir"])
		if task == "readability":
			subsDb = openSubsDb(settings["rootdir"])
			pullFeedsFromReadability(subsDb, settings["rootdir"], settings["cacheimages"], settings["readabilityapikey"])

if  __name__ =='__main__':
    main(sys.argv[1:])
