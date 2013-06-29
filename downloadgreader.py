import os
import sqlite3
import urllib2
import urllib
import time

rssToolFolder = "/Users/karlli/Desktop/rsstool/"

def scrapeArchivesFromGReader(rssToolDir):
	subsDb = sqlite3.connect(rssToolDir+'subscriptions.db')
	dbc = subsDb.cursor()
	feeds = dbc.execute('SELECT * FROM feeds').fetchall()
	#setup feeds dir
	if os.path.exists(rssToolDir+'feeds') == False:
		os.makedirs(rssToolDir+'feeds')
	j = 0
	for feed in feeds:
		#process URLs and filenames
		greaderurl = "http://www.google.com/reader/api/0/stream/contents/feed/"+urllib2.quote(feed[0], '')+"?n=9999&ot=0"
		print greaderurl
		xmlfilename = feed[0].replace('http://','').replace('/','_')
		if os.path.exists(rssToolDir+'feeds/'+xmlfilename) == False:
			os.makedirs(rssToolDir+'feeds/'+xmlfilename)
		try:
			urllib.urlretrieve(greaderurl, rssToolDir+"feeds/"+xmlfilename+"/archive.xml")
			print "Downloading archive of " + feed[0] + " from Google Reader API"
		except IOError:
			print "Delaying for server to catch up..."
			time.sleep(5)
			try:
				urllib.urlretrieve(greaderurl, rssToolDir+"feeds/"+xmlfilename+"/archive.xml")
			except IOError:
				print "Feed " + feed[0] + " archive could not be downloaded from Google Reader API"
		j = j+1

scrapeArchivesFromGReader(rssToolFolder)

