Hahli
=====

About
-----

A simple RSS archiving tool. Adds in feeds from OPML files and pulls all posts from given feeds into SQLite databases. Can also optionally download images and expand truncated feed contents with Readability.

Written as a fun little exercise in one afternoon, so don't expect it to be terribly cleverly written or appropriate for actual use. I'm also a rendering/graphics guy, not a web guy, so doubly don't expect this to be terribly clever.

Requirements
------------

* [FeedParser](http://code.google.com/p/feedparser/)
* Python 2.7

How To Use
----------

Run using:

	python hahli.py [arguments]

Supported arguments are:

* settings=[path to a settings json file]
	* By default, Hahli looks for settings in a settings.json file in the same directory. This argument overrides the default settings.json file location and filename.
* addsubs
	* Tells Hahli to add feeds from the OPML file specified in settings, and set up SQLite databases and directory structure if necessary
* update
	* Tells Hahli to update all feeds and add all new entries to databases
* checkimages
	* Tells Hahli to check all cached images for broken images and clean up broken images
* readability
	* Tells Hahli to update all truncated feeds with Readability

Settings
--------

Settings for Hahli are specified in a json file with the following format:

	{
	    "readabilityapikey": (Readability API key goes here),
	    "opml": (OPML file to add new feeds from goes here),
	    "rootdir": (Path that Hahli should build archives in),
	    "cacheimages": (true if Hahli should cache images, false if not)
	}

Settings can be overridden using the following arguments:

* readabilityapikey=[Readability API Key]
* opml=[OPML file path]
* rootdir=[Archive directory]
* cacheimages=[True or False]