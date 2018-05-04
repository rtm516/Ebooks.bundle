"""eBook and Comic reader for plex

Allows easy use of eBooks and Comics with plex
"""
import os
import sys
import json
import random
from urllib2 import urlopen, quote
# https://github.com/pmaupin/pdfrw/tree/8774f15b1189657e5c30079b4d658284660ceadc
from pdfrw import PdfReader
# https://github.com/PierreQuentel/PyDbLite/tree/a97f55ed867694b2f7798b7dc8267f18bbf1a2cc
from pydblite import Base

TITLE = "E-Books"
ART = "art-default.jpg"
ICON = "icon-default.png"  # http://www.clker.com/clipart-24891.html
BOOK = "book.png"  # http://www.clker.com/clipart-3888.html
PREFIX = "/video/ebooks"
EBOOK_FOLDER = "E:/ebooks/"

# http://openlibrary.org/search.json?title=
# http://openlibrary.org/search.json?author=

TOTALFILES = 0

class Data:
    """Stores global data

    Gives access to a series of global variables for use throughout the file
    """
    books = {}
    authors = {}
    bookDB = Base(EBOOK_FOLDER + 'books.pdl')
    authorDB = Base(EBOOK_FOLDER + 'authors.pdl')

    @staticmethod
    def debug_log(msg_str):
        """Log helper

        Prefixes a debug message with the plugin title to allow for easy search in the log

        Arguments:
            msg_str {string} -- Message to log
        """
        Log.Debug(TITLE + ": " + msg_str)


Data.debug_log("Plugin loaded")

if Data.bookDB.exists():
    Data.bookDB.open()
else:
    Data.bookDB.create("id", "file", "title", "summary", "pageCount",
                        "imageURL", "openLibraryID", "author", mode="open")
    Data.bookDB.create_index('id')
    Data.bookDB.commit()

if Data.authorDB.exists():
    Data.authorDB.open()
else:
    Data.authorDB.create("id", "name", "imageURL", "openLibraryID", mode="open")
    Data.authorDB.create_index('id')
    Data.authorDB.commit()   


class Book:
    """Book info class

    Defines the default varibales for a book and gives a fallback if there not set
    """
    filename = "unknown.pdf"
    author = "Unknown"
    author_id = ""
    title = "Untitled"
    book_id = ""
    pages = 2
    summary = "N/A"
    image = R(BOOK)


class Author:
    """Author info class

    Defines the default varibales for an author and gives a fallback if there not set
    """
    name = "Unknown"
    author_id = ""
    image = R(ART)

def get_url(url):
    """URL GET request

    Allows for returning of a string from the specified url

    Arguments:
        url {string} -- The url to send the request to

    Returns:
        string -- A string with the response if it was successful if not then an empty string
    """
    try:
        response = urlopen(url)
        return response.read()
    except Exception as dummy_ex:
        return ""

def get_json_from_url(url):
    """JSON GET request

    Allows for returning of a json object from the specified url

    Arguments:
        url {string} -- The url to send the request to

    Returns:
        object -- An object with the parsed json if it was successful if not then an empty object
    """
    try:
        json_res = get_url(url)
        json_obj = json.loads(json_res)
        return json_obj
    except Exception as dummy_ex:
        return json.loads("{}")


class DirWalker(object):
    """File listing class

    Allows for looping through a dir and listing out the files
    Based of https://ssscripting.wordpress.com/2009/03/03/python-recursive-directory-walker/
    """

    def walk(self, folder_dir, meth):
        """Directory walker

        Walks a directory recursively, and executes a callback on each file

        Arguments:
            folder_dir {string} -- Folder to search
            meth {function} -- Function to run with the found filename
        """
        folder_dir = os.path.abspath(folder_dir)
        for file in [file for file in os.listdir(folder_dir) if not file in [".", ".."]]:
            nfile = os.path.join(folder_dir, file)
            if os.path.isdir(nfile):
                self.walk(nfile, meth)
            else:
                meth(folder_dir, file)


def register_file(file_dir, filename):
    """File processing

    Takes the file and querys certain APIs to gather infomation about the book and author

    Arguments:
        file_dir {string} -- Directory of the file
        filename {string} -- Name on disk of the file
    """
    global TOTALFILES
    if filename.endswith(".pdf"):
        if len(Data.bookDB(file=filename)) >= 1:
            Data.debug_log("Found cached file: " + filename)
            return

        Data.debug_log("Getting data for: " + filename)
        try:
            pdf_data = PdfReader(os.path.join(file_dir, filename))

            tmp_book = Book()
            tmp_book.filename = filename

            if pdf_data.Info and pdf_data.Info.Title:
                tmp_book.title = pdf_data.Info.Title.strip("\"'()")

            if pdf_data.Info and pdf_data.Info.Author:
                tmp_book.author = pdf_data.Info.Author.strip("\"'()")

            rand_int = str(random.randint(100000, 999999))
            while rand_int in Data.authors:
                rand_int = str(random.randint(100000, 999999))

            tmp_book.author_id = rand_int

            url = "http://openlibrary.org/search.json?title=" + quote(os.path.splitext(filename)[0])
            json_res = get_json_from_url(url)
            if ("docs" in json_res) and (len(json_res["docs"]) >= 1):
                tmp_book.title = json_res["docs"][0]["title"]
                tmp_book.book_id = json_res["docs"][0]["edition_key"][0]
                tmp_book.author = json_res["docs"][0]["author_name"][0]
                tmp_book.author_id = json_res["docs"][0]["author_key"][0]
                tmp_book.image = "http://covers.openlibrary.org/b/olid/" + tmp_book.book_id + "-M.jpg?default=false"

            found = False
            for tmp_auth_id in Data.authors:
                tmp_aut = Data.authors[tmp_auth_id]
                if tmp_aut.name == tmp_book.author:
                    found = True
                    tmp_book.author_id = tmp_aut.author_id
                    break

            if not found:
                tmp_author = Author()
                tmp_author.name = tmp_book.author
                tmp_author.author_id = tmp_book.author_id
                tmp_author.image = "http://covers.openlibrary.org/a/olid/" + tmp_author.author_id + "-M.jpg?default=false"
                Data.authors[tmp_book.author_id] = tmp_author
                Data.authorDB.insert(id=len(Data.authorDB), name=tmp_author.name,
                                    openLibraryID=tmp_author.author_id, imageURL=tmp_author.image)
                Data.authorDB.commit()

            if len(tmp_book.summary) >= 1:
                tmp_book.summary = tmp_book.summary + "\n"

            tmp_book.summary = tmp_book.summary + "Filename: " + filename

            Data.books[filename] = tmp_book
            Data.bookDB.insert(id=len(Data.bookDB), file=filename,
                                title=tmp_book.title, summary=tmp_book.summary,
                                pageCount=tmp_book.pages, openLibraryID=tmp_book.book_id,
                                author=tmp_book.author_id, imageURL=tmp_book.image)
            Data.bookDB.commit()
            TOTALFILES = TOTALFILES + 1
        except Exception as dummy_ex:
            Data.debug_log("Unable to read file '" +
                           os.path.join(file_dir, filename) +
                           " (" + str(dummy_ex) + ")")


def Start():
    """Initial function

    This is automatically run when the file is read by plex
    """
    global TOTALFILES
    Data.debug_log("Loading books")
    DirWalker().walk(EBOOK_FOLDER, register_file)
    Data.debug_log("Finished loading " + str(TOTALFILES) +
                   " books, starting")

    Plugin.AddViewGroup("AuthorList", viewMode="List", mediaType="items")
    Plugin.AddViewGroup("BookList", viewMode="Seasons",
                        mediaType="episodes", type="list", summary=1)
    Plugin.AddViewGroup("Book", viewMode="Episodes", mediaType="items")
    Data.debug_log("Started")


ObjectContainer.title1 = TITLE
ObjectContainer.art = R(ART)

DirectoryObject.thumb = R(ICON)
DirectoryObject.art = R(ART)

EpisodeObject.thumb = R(ICON)
EpisodeObject.art = R(ART)


@handler(PREFIX, TITLE)
def MainMenu():
    """Main menu

    Generates the layout for the main menu of the plugin

    Decorators:
        handler

    Returns:
        ObjectContainer -- Built in Plex class containing the layout of the displayed panels
    """
    Data.debug_log("MainMenu")
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(load_authors), title="Authors"))
    oc.add(DirectoryObject(key=Callback(load_titles), title="Books"))

    return oc


@route(PREFIX + "/authors")
def load_authors():
    """Authors display

    Generates the layout for the authors page with all known authors

    Decorators:
        route

    Returns:
        ObjectContainer -- Built in Plex class containing the layout of the displayed panels
    """
    Data.debug_log("load_authors")
    oc = ObjectContainer(title2="Authors")
    for author in Data.authorDB:
        try:
            oc.add(
                TVShowObject(
                    key=Callback(load_author, author_id=str(author["id"])),
                    rating_key=str(author["id"]),
                    title=str(author["name"]),
                    thumb=Resource.ContentsOfURLWithFallback(str(author["imageURL"]))
                )
            )
        except Exception as dummy_ex:
            pass

    return oc


@route(PREFIX + "/author/{author_id}")
def load_author(author_id):
    """Author book display

    Generates the layout for the author's page with all known books by them

    Decorators:
        route

    Arguments:
        author_id {string} -- Unique id of the author usually from the Open Library

    Returns:
        ObjectContainer -- Built in Plex class containing the layout of the displayed panels
    """
    Data.debug_log("LoadAuthor")
    author = Data.authors[author_id]

    oc = ObjectContainer(view_group="BookList", title2=author.name)
    for book_file in Data.books:
        book = Data.books[book_file]
        if book.author_id != author.author_id:
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
        except Exception as dummy_ex:
            pass

    return oc


@route(PREFIX + "/books")
def load_titles():
    """Books display

    Generates the layout for the books page with all known books

    Decorators:
        route

    Returns:
        ObjectContainer -- Built in Plex class containing the layout of the displayed panels
    """
    Data.debug_log("load_titles")
    oc = ObjectContainer(view_group="BookList", title2="Books")

    for book in Data.bookDB:
        try:
            oc.add(
                SeasonObject(
                    key=Callback(load_book, file=str(book["file"])),
                    rating_key=str(book["file"]),
                    title="By " + str(Data.authorDB(openLibraryID=str(book["author"]))[0]["name"]),
                    show=str(book["title"]),
                    summary=str(book["summary"]),
                    episode_count=int(book["pageCount"]),
                    thumb=Resource.ContentsOfURLWithFallback(str(book["imageURL"]), fallback=BOOK)
                )
            )
        except Exception as dummy_ex:
            Data.debug_log(str(dummy_ex))
            pass

    return oc


@route(PREFIX + "/book/{file}")
def load_book(file):
    """Book display

    Generates the layout for the books's page with all pages

    Decorators:
        route

    Arguments:
        file {string} -- Unique filename of the book

    Returns:
        ObjectContainer -- Built in Plex class containing the layout of the displayed panels
    """
    Data.debug_log("load_book")
    # Get book info
    book = Data.books[file]

    oc = ObjectContainer(title2=book.title)

    # Start page loop
    for pageno in range(1, book.pages + 1):
        try:
            oc.add(
                PhotoObject(
                    key=book.title + str(pageno),
                    rating_key=book.title + str(pageno),
                    title="Page " + str(pageno),
                    summary="Page " + str(pageno) + " of " +
                    book.title + " by " + book.author,
                    thumb=R(ART)
                )
            )
        except Exception as dummy_ex:
            pass
    # End page loop

    return oc
