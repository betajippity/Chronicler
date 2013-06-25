import xml.etree.ElementTree as ET
import os
import sqlite3

opmlFile = "/Users/karlli/Desktop/subscriptions.xml"
rssToolDir = "/Users/karlli/Desktop/"

def createFeedDBFromOPML(opmlFile, rssToolDir):
	#load opml
	parseTree = ET.parse(opmlFile).getroot()
	#setup sqlite db for subscriptions
	subsDb = sqlite3.connect(rssToolDir+'subscriptions.db')
	dbc = subsDb.cursor()
	dbc.execute('''CREATE TABLE IF NOT EXISTS feeds ("feedURL" TEXT PRIMARY KEY  NOT NULL , "name" TEXT, "htmlURL" TEXT)''')
	subsDb.commit()
	#loop through subscriptions and add each subscription to subsDb
	for feed in parseTree[1]:
		id = feed.attrib['xmlUrl']
		feedQuery = (id, feed.attrib['title'], feed.attrib['htmlUrl'])
		#check if feed already exists in db and insert if it does not
		selectedRow = dbc.execute('SELECT * FROM feeds WHERE feedURL=?', (id,)).fetchone()
		if selectedRow == None:
			dbc.execute('INSERT INTO feeds VALUES (?,?,?)', feedQuery)
			subsDb.commit()
		else:
			print "Warning: Feed with URL "+feed.attrib['xmlUrl']+" already exists in db."

createFeedDBFromOPML(opmlFile, rssToolDir)
