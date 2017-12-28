"""eBook and Comic reader for plex

Allows easy use of eBooks and Comics with plex
"""
import os
import sys
import json
import random
from urllib2 import urlopen
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


class Data:
    """Stores global data

    Gives access to a series of global variables for use throughout the file
    """
    books = {}
    authors = {}
    totalFiles = 0
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

if Data.authorDB.exists():
    Data.authorDB.open()


Data.bookDB.create("id", "file", "title", "summary", "pageCount",
                   "imageURL", "openLibraryID", "author", mode="open")
Data.bookDB.create_index('id')
Data.bookDB.commit()

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


def get_json_from_url(url):
    """JSON GET request

    Allows for returning of a json object from the specified url

    Arguments:
        url {string} -- The url to send the request to

    Returns:
        object -- An object with the parsed json if it was successful if not then an empty object
    """
    try:
        response = urlopen(url)
        json_res = response.read()
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
    if filename.endswith(".pdf"):
        if Data.bookDB(file=filename):
            return

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

            json_res = get_json_from_url(
                "http://openlibrary.org/search.json?title=" + os.path.splitext(filename)[0])
            if ("docs" in json_res) and (len(json_res["docs"]) >= 1):
                tmp_book.book_id = json_res["docs"][0]["edition_key"][0]
                tmp_book.author = json_res["docs"][0]["author_name"][0]
                tmp_book.author_id = json_res["docs"][0]["author_key"][0]
                #tmp_book.image = Resource.ContentsOfURLWithFallback(url="http://covers.openlibrary.org/b/olid/" + tmp_book.book_id + "-M.jpg?default=false", fallback=R(BOOK))

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
                #tmp_author.image = Resource.ContentsOfURLWithFallback(url="http://covers.openlibrary.org/a/olid/" + tmp_author.author_id + "-M.jpg?default=false", fallback=R(ART))
                Data.authors[tmp_book.author_id] = tmp_author

            if len(tmp_book.summary) >= 1:
                tmp_book.summary = tmp_book.summary + "\n"

            tmp_book.summary = tmp_book.summary + "Filename: " + filename

            Data.books[filename] = tmp_book
            Data.bookDB.insert(id=len(Data.bookDB), file=filename,
                               title=tmp_book.title, summary=tmp_book.summary,
                               pageCount=tmp_book.pages, openLibraryID=tmp_book.book_id)
            Data.totalFiles = Data.totalFiles + 1
        except Exception as dummy_ex:
            Data.debug_log("Unable to read file '" +
                           os.path.join(file_dir, filename))


def Start():
    """Initial function

    This is automatically run when the file is read by plex
    """
    Data.debug_log("Loading books")
    DirWalker().walk(EBOOK_FOLDER, register_file)
    Data.debug_log("Finished loading " + str(Data.totalFiles) +
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
    for author_id in Data.authors:
        author = Data.authors[author_id]
        try:
            oc.add(
                TVShowObject(
                    key=Callback(load_author, author_id=author.author_id),
                    rating_key=author.id,
                    title=author.name,
                    thumb=author.image
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
                    episoddummy_excount=book.pages,
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

    for book_file in Data.books:
        book = Data.books[book_file]
        try:
            oc.add(
                SeasonObject(
                    key=Callback(load_book, file=book.filename),
                    rating_key=book.filename,
                    title="By " + book.author,
                    show=book.title,
                    summary=book.summary,
                    episoddummy_excount=book.pages,
                    thumb=book.image
                )
            )
        except Exception as dummy_ex:
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
    for pagdummy_exno in range(1, book.pages + 1):
        try:
            oc.add(
                PhotoObject(
                    key=book.title + str(pagdummy_exno),
                    rating_key=book.title + str(pagdummy_exno),
                    title="Page " + str(pagdummy_exno),
                    summary="Page " + str(pagdummy_exno) + " of " +
                    book.title + " by " + book.author,
                    thumb=R(ART)
                )
            )
        except Exception as dummy_ex:
            pass
    # End page loop

    return oc
