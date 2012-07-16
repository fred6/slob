import sys, sqlite3, time

dbpath = 'slob.sqlite'

def init():
    conn = sqlite3.connect(dbpath)
    init_sql = """
    CREATE TABLE infob (
      id int primary key,
      obj_id text UNIQUE,
      path text);

    CREATE TABLE keyword (
      id int primary key,
      keyword text);

    CREATE TABLE keyword_infob (
      iid int,
      kid int,
      PRIMARY KEY(iid, kid));

    CREATE TABLE log_entry (
      id int primary key,
      type text,
      timestamp int,
      entry text);"""

    conn.executescript(init_sql)
    conn.commit()
    conn.close()

    insert_log('auto', 'Initialized database')
    


def do_track(fpath, uid):
    # check if the path is legit somehow
    # if so, try to insert.
    # if that fails because the id wasnt unique, prompt for a unique one?
    # or you could just error for now
    conn = sqlite3.connect(dbpath)
    insert_sql = 'INSERT INTO infob (obj_id, path) VALUES (?, ?)'

    conn.execute(insert_sql, (uid, fpath))
    conn.commit()
    conn.close()

    insert_log('auto', 'Started tracking '+fpath+' as '+uid)

def insert_log(logtype, logtext):
    conn = sqlite3.connect(dbpath)
    insert_sql = 'INSERT INTO log_entry (type, timestamp, entry) VALUES (?, ?, ?)'

    conn.execute(insert_sql, (logtype, round(time.time()), logtext))
    conn.commit()
    conn.close()


def print_info(obj_id):
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()

    select_sql = """
    SELECT io.id, io.path, keys.keyword FROM infob AS io
    LEFT JOIN keyword_infob AS ki on io.id  = ki.iid 
    LEFT JOIN keyword AS keys on keys.id = ki.kid
    WHERE io.obj_id=?
    """

    c.execute(select_sql, (obj_id,))

    for row in c:
        print(obj_id+': '+row[1])

    conn.close()



def print_usage(p='a'):
    usage = {}
    usage['t'] = 'track|t  <file path> <unique id>'
    usage['v'] = 'view|v   <unique id>'
    usage['l'] = 'log|l    <text>'
    #usage['a'] = 'slob.py\n\nGrow up.\n\nOptions:\n'+'    '+usage['t']+'    '+usage['v']+'    '+usage['l']
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
        if len(sys.argv) != 4:
            print_usage('t')
        else:
            do_track(sys.argv[2], sys.argv[3])

    elif sys.argv[1] == 'log' or sys.argv[1] == 'l':
        if len(sys.argv) != 3:
            print_usage('l')
        else:
            insert_log(sys.argv[2])

    elif sys.argv[1] == 'info' or sys.argv[1] == 'i':
        if len(sys.argv) != 3:
            print_usage('i')
        else:
            print_info(sys.argv[2])

    elif sys.argv[1] == 'init':
        init()
    else:
        print_usage()

    print(sys.argv)
