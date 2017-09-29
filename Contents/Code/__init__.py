from pdfrw import PdfReader # https://github.com/pmaupin/pdfrw/tree/8774f15b1189657e5c30079b4d658284660ceadc
from urllib2 import urlopen
import os, sys, json, random

TITLE = "E-Books"
ART = "art-default.jpg"
ICON = "icon-default.png" # http://www.clker.com/clipart-24891.html
BOOK = "book.png" # http://www.clker.com/clipart-3888.html
PREFIX = "/video/ebooks"
EBOOK_FOLDER = "E:/ebooks/"

#http://openlibrary.org/search.json?title=
#http://openlibrary.org/search.json?author=

Log.Debug("Plugin loaded - PLUGIN EBOOKS")

books = {}
authors = {}
totalFiles = 0

class Book:
	filename = "unknown.pdf"
	author = "Unknown"
	authorId = ""
	title = "Untitled"
	id = ""
	pages = 2
	summary = "N/A"
	image = R(BOOK)

class Author:
	name = "Unknown"
	id = ""
	image = R(ART)

def getJSONFromURL(url):
	try:
		response = urlopen(url)
		jsonRes = response.read()
		jsonObj = json.loads(jsonRes)
		return jsonObj
	except:
		return json.loads("{}")

class DirWalker(object): # based of https://ssscripting.wordpress.com/2009/03/03/python-recursive-directory-walker/
	def walk(self,dir,meth): #walks a directory, and executes a callback on each file
		dir = os.path.abspath(dir)
		for file in [file for file in os.listdir(dir) if not file in [".",".."]]:
			nfile = os.path.join(dir,file)
			if os.path.isdir(nfile):
				self.walk(nfile,meth)
			else:
				meth(dir, file)

def registerFile(dir, filename):
	global totalFiles
	if filename.endswith(".pdf"):
		try:
			x = PdfReader(os.path.join(dir, filename))
			
			tmpBook = Book()
			tmpBook.filename = filename

			if (x.Info and x.Info.Title):
				tmpBook.title=x.Info.Title.strip("\"'()")

			if (x.Info and x.Info.Author):
				tmpBook.author=x.Info.Author.strip("\"'()")
			
			randInt = str(random.randint(100000, 999999))
			while (randInt in authors):
				randInt = str(random.randint(100000, 999999))

			tmpBook.authorId = randInt
			
			jsonRes = getJSONFromURL("http://openlibrary.org/search.json?title="+os.path.splitext(filename)[0])
			if (("docs" in jsonRes) and (len(jsonRes["docs"]) >= 1)):
				tmpBook.id = jsonRes["docs"][0]["edition_key"][0]
				tmpBook.author = jsonRes["docs"][0]["author_name"][0]
				tmpBook.authorId = jsonRes["docs"][0]["author_key"][0]
				tmpBook.image = Resource.ContentsOfURLWithFallback(url="http://covers.openlibrary.org/b/olid/" + tmpBook.id + "-M.jpg?default=false", fallback=R(BOOK))

			found = False
			for tmpAutId in authors:
				tmpAut = authors[tmpAutId]
				if tmpAut.name == tmpBook.author:
					found = True
					tmpBook.authorId = tmpAut.id
					break

			if not found:
				tmpAuthor = Author()
				tmpAuthor.name = tmpBook.author
				tmpAuthor.id = tmpBook.authorId
				tmpAuthor.image = Resource.ContentsOfURLWithFallback(url="http://covers.openlibrary.org/a/olid/" + tmpAuthor.id + "-M.jpg?default=false", fallback=R(ART))
				authors[tmpBook.authorId] = tmpAuthor

			if (len(tmpBook.summary) >= 1):
				tmpBook.summary = tmpBook.summary + "\n"    

			tmpBook.summary = tmpBook.summary + "Filename: " + filename

			books[filename] = tmpBook
			totalFiles = totalFiles + 1
		except:
			Log.Debug("Unable to read file '" + os.path.join(dir, filename) + "' - PLUGIN EBOOKS")
			pass

def Start():
	Log.Debug("Loading books - PLUGIN EBOOKS")
	DirWalker().walk(EBOOK_FOLDER, registerFile)
	Log.Debug("Finished loading " + str(totalFiles) + " books, starting - PLUGIN EBOOKS")

	Plugin.AddViewGroup("AuthorList", viewMode="List", mediaType="items")
	Plugin.AddViewGroup("BookList", viewMode="Seasons", mediaType="episodes", type="list", summary=1)
	Plugin.AddViewGroup("Book", viewMode="Episodes", mediaType="items")
	Log.Debug("Started - PLUGIN EBOOKS")

ObjectContainer.title1 = TITLE
ObjectContainer.art = R(ART)

DirectoryObject.thumb = R(ICON)
DirectoryObject.art = R(ART)

EpisodeObject.thumb = R(ICON)
EpisodeObject.art = R(ART)

@handler(PREFIX, TITLE)
def MainMenu():
	Log.Debug("MainMenu - PLUGIN EBOOKS")
	oc = ObjectContainer()
	oc.add(DirectoryObject(key=Callback(LoadAuthors), title="Authors"))
	oc.add(DirectoryObject(key=Callback(LoadTitles), title="Books"))

	return oc

@route(PREFIX + "/authors")
def LoadAuthors():
	Log.Debug("LoadAuthors - PLUGIN EBOOKS")
	oc = ObjectContainer(title2="Authors")
	for authorId in authors:
		author = authors[authorId]
		try:
			oc.add(
				TVShowObject(
					key=Callback(LoadAuthor, authorId=author.id),
					rating_key=author.id,
					title=author.name,
					thumb=author.image
				)
			)
		except:
			pass
	
	return oc

@route(PREFIX + "/author/{authorId}")
def LoadAuthor(authorId):
	Log.Debug("LoadAuthor - PLUGIN EBOOKS")
	author = authors[authorId]

	oc = ObjectContainer(view_group="BookList", title2=author.name)
	for bookFile in books:
		book = books[bookFile]
		if (book.authorId != author.id):
			continue

		try:
			oc.add(
				SeasonObject(
					key=book.filename,
					rating_key=book.filename,
					title="By " + book.author,
					show=book.title,
					summary=book.summary,
					episode_count=book.pages,
					thumb=book.image
				)
			)
		except:
			pass
	
	return oc

@route(PREFIX + "/books")
def LoadTitles():
	Log.Debug("LoadTitles - PLUGIN EBOOKS")
	oc = ObjectContainer(view_group="BookList", title2="Books")
	
	for bookFile in books:
		book = books[bookFile]
		try:
			oc.add(
				SeasonObject(
					key=Callback(LoadBook, file=book.filename),
					rating_key=book.filename,
					title="By " + book.author,
					show=book.title,
					summary=book.summary,
					episode_count=book.pages,
					thumb=book.image
				)
			)
		except:
			pass
	
	return oc

@route(PREFIX + "/book/{file}")
def LoadBook(file):
	Log.Debug("LoadBook - PLUGIN EBOOKS")
	#Get book info
	book = books[file]

	oc = ObjectContainer(title2=book.title)

	#Start page loop
	for pageNo in range(1, book.pages+1):
		try:
			oc.add(
				PhotoObject(
					key=book.title + str(pageNo),
					rating_key=book.title + str(pageNo),
					title="Page " + str(pageNo),
					summary="Page " + str(pageNo) + " of " + book.title + " by " + book.author,
					thumb=R(ART)
				)
			)
		except:
			pass
	#End page loop

	return oc
	