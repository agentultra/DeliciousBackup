import os
import sqlite3
import sys
import time

from datetime import datetime
from optparse import OptionParser

from pydelicious import DeliciousAPI


def _update_callback(current, total, size=60):
    """ Prints a basic progress bar to the console """
    x = int(size * current / total)
    sys.stdout.write("\r[%s%s] %i/%i" % ("#" * x, "." * (size - x),
                                         current, total))
    sys.stdout.flush()

    if current == total:
        print >> sys.stdout, "\n"

def _create_db(conn):
    cur = conn.cursor()
    cur.execute(('CREATE TABLE IF NOT EXISTS posts ('
                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                 'href VARCHAR(255) UNIQUE, '
                 'description VARCHAR(255), '
                 'created DATETIME)'))
    cur.execute(('CREATE TABLE IF NOT EXISTS tags ('
                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                 'name VARCHAR(255) UNIQUE)'))
    cur.execute(('CREATE TABLE IF NOT EXISTS posts_tags ('
                 'post_id INTEGER NOT NULL, '
                 'tag_id INTEGER NOT NULL, '
                 'FOREIGN KEY(post_id) REFERENCES posts (id), '
                 'FOREIGN KEY(tag_id) REFERENCES tags (id))'))
    conn.commit()

def _import_bookmarks(username, password, token='.deliciousbackup'):
    """ Import bookmarks from delicious. Returns a list of dict
    objects representing posts """
    token_path = os.path.join(os.path.abspath(os.path.expanduser('~')),
                              token)
    if os.path.exists(token_path):
        with open(token_path) as f:
            last_run = datetime.fromtimestamp(float(f.read()))
    else:
        last_run = time.time()
        with open(token_path, 'w') as f:
            f.write(str(last_run))
        last_run = datetime.fromtimestamp(last_run)

    dapi = DeliciousAPI(username, password)
    api_date = dapi.posts_update()
    api_date = api_date['update']['time']
    last_update = datetime(api_date.tm_year, api_date.tm_mon,
                           api_date.tm_mday, hour=api_date.tm_hour,
                           minute=api_date.tm_min,
                           second=api_date.tm_sec)
    if last_update > last_run:
        #last_run.microsecond=0
        posts = dapi.posts_all(fromdt=last_run.isoformat())
    else:
        posts = dapi.posts_all()

    return posts['posts']

def _import_tags(username, password):
    """ Import tags from delicious.  Returns a list of dict objects
    representing tags """
    dapi = DeliciousAPI(username, password)
    tags = dapi.tags_get()

    return tags['tags']

def _insert_posts(db, posts, callback=_update_callback):
    """ Inserts posts into our database, an optional callback can be
    provided to give progress feedback """
    cur = db.cursor()
    total = len(posts)
    for i, post in enumerate(posts):
        cur.execute(('INSERT OR IGNORE INTO posts (href, description, '
                     'created) VALUES (?,?,?)'),
                    (post['href'], post['description'], post['time']))

        if callable(callback):
            callback(i+1, total)
    db.commit()

def _insert_tags(db, tags, callback=_update_callback):
    """ Inserts tags into our database, an optional callback can be
    provided to give progress feedback"""
    cur = db.cursor()
    total = len(tags)
    for i, tag in enumerate(tags):
        cur.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag['tag'],))

        if callable(callback):
            callback(i+1, total)
    db.commit()

def _process_tags(db, posts, callback=_update_callback):
    """ Takes a list of post objects from _import_bookmarks and
    attempts to associate them with tags in the database """
    cur = db.cursor()
    total = len(posts)
    missed = []
    for i, post in enumerate(posts):
        post_id, = cur.execute('SELECT id FROM posts WHERE href = ?',
                               (post['href'],)).fetchone()
        tags = post['tag'].split(' ')
        if len(tags) > 0:
            for tag in tags:
                # Sometimes posts returned by API have different tag
                # names than the one returned by the tags_get call
                try:
                    tag_id, tag_name = cur.execute(('SELECT * FROM tags WHERE '
                                                    'name = ?'), (tag,)).\
                                                    fetchone()
                except TypeError:
                    # we try a simple strategy, try lowering the string
                    try:
                        tag_id, tag_name = cur.execute(('SELECT * FROM tags '
                                                        'WHERE name = ?'),
                                                       (tag.lower(),)).\
                                                       fetchone()
                    except:
                        # if we still cannot find it, echo it to a
                        # list to notify the user later
                        missed.append((tag, post_id))
                        continue
                # check to see if we already associated this tag to this post
                check, = cur.execute(('SELECT count(*) FROM posts_tags WHERE '
                                      'post_id = ? AND tag_id = ?'),
                                     (post_id, tag_id)).fetchone()
                if check == 0:
                    # create the association
                    cur.execute(('INSERT INTO posts_tags (post_id, tag_id) '
                                 'VALUES (?, ?)'), (post_id, tag_id))
        if callable(callback):
            callback(i+1, total)
    db.commit()
    if len(missed) > 0:
        print >> sys.stderr, "Error associating the following: %s" % missed

def backup(username, password, database='bookmarks.db', create=False):
    """ Downloads a users' del.icio.us bookmarks to a local sqlite3
    database """
    db = sqlite3.connect(database)

    if create:
        _create_db(db)

    print >> sys.stdout, "Fetching bookmarks from Delicious (may take a while)"
    posts = _import_bookmarks(username, password)
    print >> sys.stdout, "Importing bookmarks"
    _insert_posts(db, posts)
    print >> sys.stdout, "Fetching tags from Delicious (may take a while)"
    tags = _import_tags(username, password)
    print >> sys.stdout, "Importing tags"
    _insert_tags(db, tags)
    print >> sys.stdout, "Processing tags"
    _process_tags(db, posts, tags)
    print >> sys.stdout, "Done!"

def main():
    parser = OptionParser()
    parser.add_option('-u', '--username', dest='username', metavar='USERNAME',
                      help='your del.icio.us username')
    parser.add_option('-p', '--password', dest='password', metavar='PASSWORD',
                      help='your del.icio.us password')
    parser.add_option('-f', '--file', dest='database', metavar='FILE',
                      help='filename to store bookmarks in')
    (options, args) = parser.parse_args()

    if options.username and options.password:
        if options.database:
            backup(options.username, options.password,
                   database=options.database, create=True)
        else:
            backup(options.username, options.password, create=True)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
