import sys, sqlite3, time, datetime, re

conn = None

def init():
    init_sql = """
    CREATE TABLE infob (
      id integer primary key autoincrement,
      alias text UNIQUE,
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

    insert_log('auto', 'Initialized database')
    


def do_track(fpath, uid, **kwargs):
    # check if the path is legit somehow
    # if so, try to insert.
    # if that fails because the id wasnt unique, prompt for a unique one?
    # or you could just error for now

    c = conn.cursor()
    sql = 'INSERT INTO infob (alias, path) VALUES (?, ?)'

    c.execute(sql, (uid, fpath))

    if kwargs.get('tags') != None:
        add_tags_to_infob(c, c.lastrowid, kwargs['tags'])

    conn.commit()

    insert_log('auto', 'Started tracking '+fpath+' as '+uid)

# take in  partial alias, return iid (after user prompting) or None
def match_partial_alias(cursor, alias):
    sql = 'SELECT id, alias FROM infob WHERE alias LIKE ?'
    cursor.execute(sql, ('%'+alias+'%',))

    poss = cursor.fetchall()

    if len(poss) > 0:
        if len(poss) == 1 and poss[0][1] == alias:
            return poss[0][0]
        else:
            sel = None
            while sel != 0 and sel not in [p[0] for p in poss]:
                print('Possible matches:')
                print('   '.join(['('+str(p[0])+') '+p[1] for p in poss]), end='')
                print('   (0) [None]')
                sel = int(input('>>> '))

            if sel != 0:
                return sel
            else:
                return None
    else:
        return None


def insert_log(logtype, logtext):
    c = conn.cursor()

    m = re.findall('\[\[([A-Za-z0-9_ ]+)\]\]', logtext)

    # only autocomplete/reference 1 for the moment. want to test.
    if m != []:
        ref_iids = []
        abort = False

        for match in m:
            ref_iid = match_partial_alias(c, match)

            if ref_iid != None:
                ref_iids.append(ref_iid)
                # replace the bracketed stuff with the IID
                partialstr = '[['+match+']]'
                iidstr = '[['+str(ref_iid)+']]'
                logtext = logtext.replace(partialstr, iidstr, 1)
            else:
                abort = True

        if not abort:
            sql = 'INSERT INTO log_entry (type, timestamp, entry) VALUES (?, ?, ?)'
            c.execute(sql, (logtype, round(time.time()), logtext))
            lid = c.lastrowid


            for ref_iid in ref_iids:
                sql = 'INSERT INTO infob_log (lid, iid) VALUES (?, ?)'
                c.execute(sql, (lid, ref_iid))

    else:
        sql = 'INSERT INTO log_entry (type, timestamp, entry) VALUES (?, ?, ?)'
        c.execute(sql, (logtype, round(time.time()), logtext))

    conn.commit()


def print_info(alias, **kwargs):
    c = conn.cursor()

    if kwargs.get('iid') != None:
        ref_iid = kwargs['iid']
    else:
        ref_iid = match_partial_alias(c, alias)

    if ref_iid != None:
        select_sql = """
        SELECT io.alias, io.path, tag.tag FROM infob io
        LEFT JOIN tag_infob ti on io.id  = ti.iid 
        LEFT JOIN tag on tag.id = ti.tid
        WHERE io.id=?
        """

        c.execute(select_sql, (ref_iid,))

        rows = c.fetchall()

        print(rows[0][0]+': '+rows[0][1])
        print('==========')

        print(', '.join([row[2] for row in rows if row[2] != None]))
        print()



def add_tags_to_infob(c, iid, tags):
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


def modify_info(alias, command, **kwargs):
    c = conn.cursor()

    iid = match_partial_alias(c, alias)

    if iid != None:
        if command == 't+':
            add_tags_to_infob(c, iid, kwargs['tags'])
        elif command == 't-':
            for tag in kwargs['tags']:
                sql = 'SELECT * FROM tag WHERE tag=?'
                c.execute(sql, (tag,))
                tres = c.fetchone()

                sql = 'DELETE FROM tag_infob WHERE iid=? and tid=?'
                c.execute(sql, (iid, tres[0]))

        else:
            print(kwargs['new_alias'])
            sql = 'UPDATE infob SET alias=? WHERE id=?'
            c.execute(sql, (kwargs['new_alias'], iid))
            # so ugly
            alias = kwargs['new_alias']

        conn.commit()
    else:
        pass

    print_info(alias, iid=iid)


def query_objects(criteria):
    c = conn.cursor()

    sql = 'SELECT * FROM infob WHERE alias LIKE ? or path LIKE ?'
    percents = '%'+criteria+'%'

    for row in c.execute(sql, (percents, percents)):
        print_info(row[1], iid=row[0])



def query_tags(criteria):
    # we just do one tag only for now. eventually should be able to filter by many
    # also, need to be able to differentiate between exact and partial searching. right now we search partial by default
    c = conn.cursor()

    sql = """
    SELECT infob.id, infob.alias FROM tag
    LEFT JOIN tag_infob ti on tag.id = ti.tid
    LEFT JOIN infob on infob.id = ti.iid
    WHERE tag LIKE ?
    """

    percents = '%'+criteria+'%'

    iids = []
    for row in c.execute(sql, (percents,)):
        if row[0] not in iids:
            print_info(row[1], iid=row[0])
            iids.append(row[0])



def query_logs(criteria):
    # only allow one search criterion for now. however we can search in two ways:
    # 1) search for entries containing that text.
    # 2) search for entries referencing this partial alias
    # 3) date ranges too!

    # let's do 1 for now.
    c = conn.cursor()

    sql = 'SELECT timestamp, entry FROM log_entry WHERE entry LIKE ?'
    percents = '%'+criteria+'%'

    for row in c.execute(sql, (percents,)):
        print(datetime.datetime.fromtimestamp(row[0]).isoformat())
        print('---------------------')
        print(row[1])
        print()


def query_logs_alias(criteria):
    # only allow one search criterion for now. however we can search in two ways:
    # 1) search for entries containing that text.
    # 2) search for entries referencing this partial alias
    # 3) date ranges too!

    # let's do 2 for now.
    c = conn.cursor()

    sql = """SELECT timestamp, entry FROM log_entry 
    LEFT JOIN infob_log ON infob_log.lid = log_entry.id
    LEFT JOIN infob ON infob.id = infob_log.iid
    WHERE infob.alias LIKE ?"""
    percents = '%'+criteria+'%'

    for row in c.execute(sql, (percents,)):
        print(datetime.datetime.fromtimestamp(row[0]).isoformat())
        print('---------------------')
        print(row[1])
        print()

def query_logs_history(length=5):
    # only allow one search criterion for now. however we can search in two ways:
    # 1) search for entries containing that text.
    # 2) search for entries referencing this partial alias
    # 3) date ranges too!

    # let's do 2 for now.
    c = conn.cursor()

    sql = 'SELECT timestamp, entry FROM log_entry ORDER BY timestamp DESC LIMIT ?'

    for row in c.execute(sql, (length,)):
        print(datetime.datetime.fromtimestamp(row[0]).isoformat())
        print('---------------------')
        print(row[1])
        print()

def dump():
    c = conn.cursor()

    tables = ['infob', 'tag', 'tag_infob', 'log_entry', 'infob_log']

    for table in tables:
        print('\n'+table+'\n==================')
        c.execute('SELECT * FROM '+table)
        for row in c:
            print(row)
            


class commandParseException(Exception):
    def __init__(self, value):
        self.value = value


class commandHandler:
    def __init__(self, cmd):
        commands = [['track', 't'],
                    ['log', 'l'],
                    ['info', 'i'],
                    ['query', 'q'],
                    ['init'],
                    ['dump']]

        self.command = None

        for c in commands:
            canon = c[0]
            for ceq in c:
                if cmd == ceq:
                    self.command = canon

    
    def parse_args(self, args):
        if self.command == None:
            raise commandParseException("aint no command brah")
        else:
            getattr(self, "parse_"+self.command)(args)


    def parse_track(self, args):
        print(args)
        if len(args) == 2:
            do_track(args[0], args[1])
        elif len(args) > 2:
            do_track(args[0], args[1], tags=args[2:])
        else:
            raise commandParseException('track arguments not valid')
        
    def parse_log(self, args):
        if len(args) == 1:
            insert_log('manual', args[0])
        else:
            raise commandParseException('log arguments not valid')
        
    def parse_info(self, args):
        if len(args) != 1:
            if len(args) > 2 and (args[1] in ['t+', 't-']):
                modify_info(args[0], args[1], tags=args[2:])
            elif len(args) > 2 and args[1] == 'c':
                modify_info(args[0], args[1], new_alias=args[2])
            else:
                raise commandParseException('info arguments not valid')
        else:
            print_info(args[0])

    def parse_query(self, args):
        if len(args) not in [1, 2] or args[0] not in ['o', 't', 'l', 'la', 'lh']:
            raise commandParseException('query arguments not valid')
        else:
            if args[0] == 'o':
                query_objects(args[1])
            elif args[0] == 't':
                query_tags(args[1])
            elif args[0] == 'l':
                query_logs(args[1])
            elif args[0] == 'la':
                query_logs_alias(args[1])
            elif args[0] == 'lh':
                if len(args) == 2:
                    query_logs_history(args[1])
                else:
                    query_logs_history()



    def parse_init(self, args):
        init()

    def parse_dump(self, args):
        dump()


def print_usage():
    usage = {}
    usage['t']    = 't  <file path> <alias> [<keyword>...]'
    usage['v']    = 'v   <unique id>'
    usage['l']    = 'l    <text>'
    usage['i']    = 'i   [t+ | t- <tag>...] [c <new alias>]'
    usage['q']    = 'q  [o | t | l | la | lh] <text>'
    usage['init'] = 'init'
    usage['dump'] = 'dump'
    begin_str = '\nslob.py <command> [<args>]\n\nCommands/options:\n   ' 
    print(begin_str + '\n   '.join([l for l in usage.values()]))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_usage()

    else:
        ch = commandHandler(sys.argv[1])
        try:
            conn = sqlite3.connect('slob.sqlite')
            ch.parse_args(sys.argv[2:])
            conn.close()
        except commandParseException as e:
            print(e.value)
            print_usage()

