import sys, sqlite3, time, re

dbpath = 'slob.sqlite'

def init():
    conn = sqlite3.connect(dbpath)
    init_sql = """
    CREATE TABLE infob (
      id integer primary key autoincrement,
      obj_id text UNIQUE,
      path text);

    CREATE TABLE tag (
      id integer primary key autoincrement,
      tag text);

    CREATE TABLE tag_infob (
      iid int,
      tid int,
      PRIMARY KEY(iid, tid));

    CREATE TABLE infob_log (
      lid int,
      iid int,
      PRIMARY KEY(lid, iid));

    CREATE TABLE log_entry (
      id integer primary key autoincrement,
      type text,
      timestamp int,
      entry text);"""

    conn.executescript(init_sql)
    conn.commit()
    conn.close()

    insert_log('auto', 'Initialized database')
    


def do_track(fpath, uid, **kwargs):
    # check if the path is legit somehow
    # if so, try to insert.
    # if that fails because the id wasnt unique, prompt for a unique one?
    # or you could just error for now

    # should be able to add keywords upon track initialization
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    sql = 'INSERT INTO infob (obj_id, path) VALUES (?, ?)'

    c.execute(sql, (uid, fpath))

    if kwargs.get('tags') != None:
        add_tags_to_infob(conn, c.lastrowid, kwargs['tags'])

    conn.commit()
    conn.close()

    insert_log('auto', 'Started tracking '+fpath+' as '+uid)


def insert_log(logtype, logtext):
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()

    m = re.findall('\[\[([A-Za-z0-9_ ]+)\]\]', logtext)

    # only autocomplete/reference 1 for the moment. want to test.
    if m != []:
        sql = 'SELECT id, obj_id FROM infob WHERE obj_id LIKE ?'
        c.execute(sql, ('%'+m[0]+'%',))
        possibles = c.fetchall()

        if len(possibles) > 0:
            print(' '.join([p[1] for p in possibles]))
            sel = int(input('>>> '))

            ref_iid = possibles[sel][0]

            # replace the bracketed stuff with the IID
            logtext.replace('[['+m[0]+']]', '[['+ref_iid+']]')            

            sql = 'INSERT INTO log_entry (type, timestamp, entry) VALUES (?, ?, ?)'
            c.execute(sql, (logtype, round(time.time()), logtext))
            lid = c.lastrowid


            sql = 'INSERT INTO infob_log (lid, iid) VALUES (?, ?)'
            c.execute(sql, (lid, ref_iid))

    else:
        sql = 'INSERT INTO log_entry (type, timestamp, entry) VALUES (?, ?, ?)'
        c.execute(sql, (logtype, round(time.time()), logtext))

    conn.commit()
    conn.close()


def print_info(obj_id):
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()

    # we should not require the full obj_id, but should do a lookup on partials as well.
    # whenever we require an obj_id passed in from command line, run the autocompleter

    select_sql = """
    SELECT io.id, io.path, tag.tag FROM infob io
    LEFT JOIN tag_infob ti on io.id  = ti.iid 
    LEFT JOIN tag on tag.id = ti.tid
    WHERE io.obj_id=?
    """

    c.execute(select_sql, (obj_id,))

    rows = c.fetchall()

    print(obj_id+': '+rows[0][1])
    print('==========')

    print(', '.join([row[2] for row in rows if row[2] != None]))
    print()
    conn.close()


def add_tags_to_infob(conn, iid, tags):
    c = conn.cursor()

    for tag in tags:
        sql = 'SELECT * FROM tag WHERE tag=?'
        c.execute(sql, (tag,))
        tres = c.fetchone()

        # if the tag aint in the table, add it
        if tres == None:
            sql = 'INSERT INTO tag (tag) VALUES (?)'
            c.execute(sql, (tag,))
            tid = c.lastrowid
        else:
            tid = tres[0]

        sql = 'INSERT INTO tag_infob (iid, tid) VALUES (?, ?)'
        c.execute(sql, (iid, tid))


def modify_info(obj_id, command, **kwargs):
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()

    sql = 'SELECT id FROM infob WHERE obj_id=?'
    c.execute(sql, (obj_id,))
    fetch = c.fetchone()
    iid = fetch[0]

    if command == 't+':
        add_tags_to_infob(conn, iid, kwargs['tags'])
    elif command == 't-':
        for tag in kwargs['tags']:
            sql = 'SELECT * FROM tag WHERE tag=?'
            c.execute(sql, (tag,))
            tres = c.fetchone()

            sql = 'DELETE FROM tag_infob WHERE iid=? and tid=?'
            c.execute(sql, (iid, tres[0]))

    else:
        print(kwargs['new_obj_id'])
        sql = 'UPDATE infob SET obj_id=? WHERE id=?'
        c.execute(sql, (kwargs['new_obj_id'], iid))
        # so ugly
        obj_id = kwargs['new_obj_id']

        
    conn.commit()
    conn.close()
    print_info(obj_id)



def dump():
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()

    tables = ['infob', 'tag', 'tag_infob', 'log_entry', 'infob_log']

    for table in tables:
        print('\n'+table+'\n==================')
        c.execute('SELECT * FROM '+table)
        for row in c:
            print(row)
            


def print_usage(p='a'):
    usage = {}
    usage['t'] = 'track|t  <file path> <unique id>'
    usage['v'] = 'view|v   <unique id>'
    usage['l'] = 'log|l    <text>'
    usage['i'] = 'info|i   [<+|-> <tag>]'
    usage['a'] = ['slob.py <command> [<args>]\n\nCommands/options:',
                 '\n    '+usage['t'],
                 '\n    '+usage['v'],
                 '\n    '+usage['l']]
    usage['a'] = ''.join(usage['a'])

    print(usage[p])

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_usage()

    elif sys.argv[1] == 'view' or sys.argv[1] == 'v':
        if len(sys.argv) != 3:
            print_usage('v')
        else:
            do_view(sys.argv[2])

    elif sys.argv[1] == 'track' or sys.argv[1] == 't':
        if len(sys.argv) == 4:
            do_track(sys.argv[2], sys.argv[3])
        elif len(sys.argv) > 4:
            do_track(sys.argv[2], sys.argv[3], tags=sys.argv[4:])
        else:
            print_usage('t')

    elif sys.argv[1] == 'log' or sys.argv[1] == 'l':
        if len(sys.argv) != 3:
            print_usage('l')
        else:
            insert_log('manual', sys.argv[2])

    elif sys.argv[1] == 'info' or sys.argv[1] == 'i':
        if len(sys.argv) != 3:
            if len(sys.argv) > 4 and (sys.argv[3] in ['t+', 't-']):
                modify_info(sys.argv[2], sys.argv[3], tags=sys.argv[4:])
            elif len(sys.argv) > 4 and sys.argv[3] == 'c':
                modify_info(sys.argv[2], sys.argv[3], new_obj_id=sys.argv[4])
            else:
                print_usage('i')
        else:
            print_info(sys.argv[2])

    elif sys.argv[1] == 'init':
        init()
    elif sys.argv[1] == 'dump':
        dump()
    else:
        print_usage()
