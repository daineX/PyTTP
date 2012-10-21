# -*- coding: utf-8 -*-

import time
import sys
import re

from sql_statements import SelectStatement

globalConnObj = None

class ConnectionProxy(object):

    def __init__(self, conn):
        self.__dict__["conn"] = conn
        self.__dict__["num_executes"] = 0

    def __getattr__(self, value):
        return getattr(self.conn, value)

    def reset_executes(self):
        self.num_executes = 0

    def __setattr__(self, key, value):
        if key in self.__dict__:
            self.__dict__[key] = value
        else:
            setattr(self.conn, key, value)

    def execute(self, *args, **kwargs):
        self.num_executes += 1
        return self.conn.execute(*args, **kwargs)

def create_sqlite3_connection(database):
    import sqlite3
    conn = sqlite3.connect(database, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn = ConnectionProxy(conn)
    return conn

class hasField(object):
    
    fieldDefs = {}
    
    def __init__(self, type, name, unique = False, restrictor = None):
        self.__class__.fieldDefs[name] = (type, unique, restrictor)
    
    @classmethod
    def clear(cls):
        cls.fieldDefs = {}


class hasKey(object):
    
    key_name = None
    key_autoinc = True

    def __init__(self, key_name, key_autoinc = True):
        self.__class__.key_name = key_name
        self.__class__.key_autoinc = key_autoinc
        
    @classmethod
    def clear(cls):
        cls.key_name = None
        cls.key_autoinc = True

class hasMany(object):
    
    refs = []
    
    def __init__(self, ref, alias=""):
        self.__class__.refs.append((ref, alias))
        
    @classmethod
    def clear(cls):
        cls.refs = []
        
        
class hasA(object):
    
    refs = []
    
    def __init__(self, ref, alias=""):
        self.__class__.refs.append((ref, alias))
        
    @classmethod
    def clear(cls):
        cls.refs = []


class DataBaseException(Exception):
    pass

class DataBaseType(object):
    
    def __init__(self):
        pass
    
    def __call__(self, value=None):
        return repr(value)
    
    def toPy(self, strRepr):
        return strRepr

class DataBaseArray(DataBaseType):
    
    
    def __init__(self, pyType):
        self.pyType = pyType
        
    def __call__(self, pyArray=None):
        if pyArray is None:
            return ""
        try:
            strRepr = '\0'.join(str(self.pyType(entry)) for entry in pyArray)
        except:
            raise DataBaseException("Invalid value in array.")
        return strRepr
        
    def toPy(self, strRepr):
        return [self.pyType(entry) for entry in strRepr.split('\0') if entry]

class DataBaseDate(DataBaseType):
    
    def __init__(self):
        pass

        
    def datetimeToUnixTime(self, dt):
        import time
        return time.mktime(dt.timetuple())+1e-6*dt.microsecond
    
    def __call__(self, value=None):
        import datetime
        if value is None:
            return str(self.datetimeToUnixTime(datetime.datetime.now()))
        if isinstance(value, datetime.datetime):
            return str(self.datetimeToUnixTime(value))
        else:
            return str(value)

    def toPy(self, strRepr):
        import datetime
        return datetime.datetime.fromtimestamp(float(strRepr))

class DataBaseBool(DataBaseType):
    
    def __init__(self):
        pass
    
    def __call__(self, value=None):
        if value:
            return "."
        else:
            return ""
    
    def toPy(self, strRepr):
        return bool(strRepr)


class MetaDataBaseObj(type):
    

    def __init__(cls, name, bases, dct):
        super(MetaDataBaseObj, cls).__init__(name, bases, dict)

        ### building fields 
        setattr(cls, "fieldTypes", {})
        setattr(cls, "fieldUniques", {})
        setattr(cls, "restrictors", {})
        setattr(cls, "has_many", [])
        setattr(cls, "ref_alias", {})
        setattr(cls, "singular_refs", [])
        setattr(cls, "belongs_to", [])
        setattr(cls, "key_name", None)
        setattr(cls, "key_autoinc", True)
        setattr(cls, "connObj", globalConnObj)
        
        for name, (type, unique, restrictor) in hasField.fieldDefs.items():
            cls.fieldTypes[name] = type
            cls.fieldUniques[name] = unique
            if restrictor and callable(restrictor):
                cls.restrictors[name] = restrictor
        
        
        cls.fieldTypes["cdate"] = float
        cls.fieldUniques["cdate"] = False
        
        hasField.clear()
        
        if hasKey.key_name:
            cls.key_name = hasKey.key_name
            cls.key_autoinc = hasKey.key_autoinc
        else:
            cls.fieldTypes["id"] = int
            cls.key_name = "id"
            cls.key_autoinc = True
        hasKey.clear()
        
        for ref, alias in hasMany.refs:
            cls.hasMany(ref, alias)
        hasMany.clear()
        
        for ref, alias in hasA.refs:
            cls.hasA(ref, alias)
        hasA.clear()
        
    def __iter__(cls):
        return cls._iter_wrapper()



class DataBaseObj(object):
    __metaclass__ = MetaDataBaseObj

    _autocommit = False
    
    
    sqlMapping = {
        None   : 'NULL',
        int    : 'INTEGER',
        long   : 'INTEGER',
        float  : 'REAL',
        str    : 'TEXT',
        unicode: 'TEXT',
        buffer : 'BLOB'
    }
    
    
    #has_many = []
    #fieldTypes = {}
    #fieldUniques = {}
    #key_name = None
    #key_autoinc = True
    #connObj = None
    
    def __init__(self, **attrs):
        self.__dict__["fieldValues"] = {}
        for key, value in self.__class__.fieldTypes.items():
            self.fieldValues[key] = value()
        for name in attrs:
            if name in self.__class__.fieldTypes and name != "cdate":
                value = attrs[name]
                if self.__class__.fieldTypes[name] == unicode:
                    if isinstance(value, unicode):
                        castValue = value
                    else:
                        castValue = unicode(value.decode("utf-8"))
                else:
                    castValue = self.__class__.fieldTypes[name](value)

                if name in self.__class__.restrictors:
                    if not self.__class__.restrictors[name](castValue):
                        raise DataBaseException("Invalid value %s for field \"%s\" ; failed restrictor %s" % (`castValue`, name, `self.__class__.restrictors[name]`))
                self.fieldValues[name] = castValue
        self.fieldValues["cdate"] = time.time()

            
    def __eq__(self, other):
        cls = self.__class__
        ocls = other.__class__
        if cls != ocls:
            return False
        return self.id == other.id


    @classmethod
    def _setConnObj(cls, connObj):
        cls.connObj = connObj


    def isSaved(self):
        return bool(getattr(self, self.__class__.key_name))


    def save(self):
        if self.isSaved():
            self.__class__.update(self)
        else:
            self.__class__.new(inst=self)

    @property
    def autocommit(self):
        return self.__class__._autocommit


    @classmethod
    def update(cls, inst):
        conn = cls.conn()
        query = "update %s set %s where %s = ?"
        names = []
        inserts = []
        values = []
        for name, value in inst.fieldValues.items():
            if name != cls.key_name:
                names.append("%s = ?" % name)
                values.append(value)
        values.append(getattr(inst, cls.key_name))
        query = query % (cls.__name__, ', '.join(names), cls.key_name)
        c = conn.cursor()
        c.execute(query, tuple(values))
        conn.commit()


    @classmethod
    def new(cls, inst=None, **attrs):
        conn = cls.conn()
        if not inst:
            inst = cls(**attrs)

        query = "insert into %s (%s) values (%s)"
        names = []
        inserts = []
        values = []
        for name, value in inst.fieldValues.items():
            if name != cls.key_name:
                names.append(name)
                inserts.append('?')
                values.append(value)
        query = query % (cls.__name__, ', '.join(names), ', '.join(inserts))
        c = conn.cursor()
        c.execute(query, tuple(values))
        conn.commit()
        if not getattr(inst, cls.key_name):
            key = list(c.execute("select last_insert_rowid();"))[0][0]
            inst.fieldValues[cls.key_name] = key
        return inst
   
    @classmethod
    def delete(cls, inst, deleteRefs=[]):
        for refClass in cls.has_many:
            refs = inst.getRefs(refClass)
            for ref in refs:
                inst.deleteRef(ref)
                if refClass in deleteRefs:
                    refClass.delete(ref)
        for refClass in cls.belongs_to:
            refs = inst.getRefs(refClass)
            for ref in refs:
                ref.deleteRef(inst)
        tableName = cls.__name__
        inst_id = getattr(inst, cls.key_name)
        template = '''delete from %s where %s=?'''
        query = template % (tableName, cls.key_name)
        cls.conn().execute(query, (inst_id,))
        cls.conn().commit()
    
    def __getattr__(self, attr):
        if attr in self.fieldValues:
            if isinstance(self.__class__.fieldTypes[attr], DataBaseType):
                return self.__class__.fieldTypes[attr].toPy(self.fieldValues[attr])
            return self.fieldValues[attr]
        if attr in self.__class__.ref_alias:
            ref = self.__class__.ref_alias[attr]
            if ref in self.__class__.singular_refs:
                return list(self.getRefs(ref))[0]
            return self.getRefs(ref)
        for ref in self.__class__.has_many:
            if attr == ref.__name__:
                if ref in self.__class__.singular_refs:
                    return list(self.getRefs(ref))[0]
                return self.getRefs(ref)
        for ref in self.__class__.belongs_to:
            if attr == ref.__name__:
                return self.getRefs(ref)                
        raise AttributeError
        
    def __setattr__(self, attr, value):
        if attr in self.fieldValues:
            cls = self.__class__
            if cls.fieldTypes[attr] == unicode:
                if isinstance(value, unicode):
                    castValue = value
                else:
                    castValue = unicode(value.decode("utf-8"))
            else:
                castValue = cls.fieldTypes[attr](value)
            if attr in cls.restrictors:
                if not cls.restrictors[attr](castValue):
                    raise DataBaseException("Invalid value %s for field \"%s\" ; failed restrictor %s" % (`castValue`, attr, `cls.restrictors[attr]`))
            if self.autocommit:
                self._dataBaseSetWrap(attr, castValue)
            self.fieldValues[attr] = castValue
        else:
            self.__dict__[attr] = value
            
    def setRef(self, inst):
        if not isinstance(inst, DataBaseObj):
            raise DataBaseException("Reference is not of type DataBaseObj!")
        ref = inst.__class__
        cls = self.__class__
        if ref in self.__class__.has_many:
            clsID = "%s_id" % (cls.__name__)
            refID = "%s_id" % (ref.__name__)
            self_id = getattr(self, cls.key_name)
            inst_id = getattr(inst, ref.key_name)            
            tableName = cls.__name__ + "_to_" + ref.__name__

            set_template = '''insert into %(tableName)s (%(clsID)s, %(refID)s) values (?, ?)'''
            valueTuple = (self_id, inst_id)
            if ref in self.__class__.singular_refs:
                template = '''select count(*) from %s where %s = ?'''
                query = template % (tableName, clsID)
                res = list(cls.conn().execute(query, (self_id,)))
                if res[0]['count(*)']:
                    set_template = '''update %(tableName)s set %(refID)s = ? where %(clsID)s = ?'''
                    valueTuple = (inst_id, self_id)
            query = set_template % dict(tableName=tableName, refID=refID, clsID=clsID)
            cls.conn().execute(query, valueTuple)
            cls.conn().commit()
        else:
            raise DataBaseException("Unknown ref type")

    def hasRef(self, inst):
        if not isinstance(inst, DataBaseObj):
            raise DataBaseException("Reference is not of type DataBaseObj!")
        ref = inst.__class__
        cls = self.__class__
        if ref in self.__class__.has_many:
            tableName = cls.__name__ + "_to_" + ref.__name__
        elif ref in self.__class__.belongs_to:
            tableName = ref.__name__ + "_to_" + cls.__name__       
        else:
            raise DataBaseException("Unknown ref type")   
        inst_id = getattr(inst, ref.key_name)
        self_id = getattr(self, cls.key_name)
        tableName = cls.__name__ + "_to_" + ref.__name__
        clsID = "%s_id" % (cls.__name__)
        refID = "%s_id" % (ref.__name__)
        template = '''select * from %s where %s=? and %s=?'''
        query = template % (tableName, clsID, refID)
        res = list(cls.conn().execute(query, (self_id, inst_id)))
        if len(res):
            return True
        else:
            return False


    def deleteRef(self, inst):
        if not isinstance(inst, DataBaseObj):
            raise DataBaseException("Reference is not of type DataBaseObj!")
        ref = inst.__class__
        cls = self.__class__
        if ref in self.__class__.has_many:
            tableName = cls.__name__ + "_to_" + ref.__name__
        elif ref in self.__class__.belongs_to:
            tableName = ref.__name__ + "_to_" + cls.__name__       
        else:
            raise DataBaseException("Unknown ref type")    
        inst_id = getattr(inst, ref.key_name)
        self_id = getattr(self, cls.key_name)
        template = '''delete from %s where %s=? and %s=?'''
        tableName = cls.__name__ + "_to_" + ref.__name__
        clsID = "%s_id" % (cls.__name__)
        refID = "%s_id" % (ref.__name__)

        query = template % (tableName, clsID, refID)
        cls.conn().execute(query, (self_id, inst_id))
        cls.conn().commit()


    def getRefs(self, ref):
        if not issubclass(ref, DataBaseObj):
            raise DataBaseException("Reference %s is not a subclass of DataBaseObj!" % ref)
        
        cls = self.__class__
        if ref in self.__class__.has_many:
            tableName = cls.__name__ + "_to_" + ref.__name__
        elif ref in self.__class__.belongs_to:
            tableName = ref.__name__ + "_to_" + cls.__name__       
        else:
            raise DataBaseException("Unknown ref type")            

        template = '''select %s from %s inner join %s where %s = ? and %s = %s'''

        clsID = "%s_id" % (cls.__name__)
        refID = "%s_id" % (ref.__name__)
        refKey = ref.key_name
        fields = ', '.join(ref.fieldTypes)
        refTableName = ref.__name__
        instID = getattr(self, cls.key_name)
        query = template % (fields, tableName, refTableName, clsID, refID, refKey)
        for row in cls.conn().execute(query,(instID,)):
            yield ref.fromAttrs(**row)

    def getRef(self, ref):
        return self.getRefs(ref).next()
    
    def getRefCount(self, ref):
        if ref in self.__class__.ref_alias:
            ref = self.__class__.ref_alias[ref]
        if not issubclass(ref, DataBaseObj):
            raise DataBaseException("Reference %s is not a subclass of DataBaseObj!" % ref)
        
        cls = self.__class__
        if ref in self.__class__.has_many:
            tableName = cls.__name__ + "_to_" + ref.__name__
        elif ref in self.__class__.belongs_to:
            tableName = ref.__name__ + "_to_" + cls.__name__       
        else:
            raise DataBaseException("Unknown ref type")            

        template = '''select count(*) from %s inner join %s where %s = ? and %s = %s'''

        clsID = "%s_id" % (cls.__name__)
        refID = "%s_id" % (ref.__name__)
        refKey = ref.key_name
        refTableName = ref.__name__
        instID = getattr(self, cls.key_name)
        query = template % (tableName, refTableName, clsID, refID, refKey)
        return list(cls.conn().execute(query, (instID,)))[0][0]
    
    def _dataBaseSetWrap(self, attr, value):
        query = "update %s set %s = ? where %s=%s"
        query = query % (self.__class__.__name__, attr, self.__class__.key_name, self.fieldValues[self.__class__.key_name])
        c = self.__class__.conn().cursor()
        c.execute(query, (value,))
        self.__class__.conn().commit()
        
    
    @classmethod
    def conn(cls):
        if cls.connObj:
            return cls.connObj
        else:
            if globalConnObj:
                return globalConnObj
            else:
                raise DataBaseException("No connection object set!")
    
    @classmethod
    def addField(cls, type, name, unique = False):
        cls.fieldTypes[name] = type
        cls.fieldUniques[name] = unique
        
    @classmethod
    def fieldDef(cls):
        pass
    
    @classmethod
    def setKey(cls, name, autoIncrement=True):
        cls.key_name = name
        cls.key_autoinc = autoIncrement
        
    def show(self):
        return "%s(%s)" % (self.__class__.__name__, ', '.join("%s=%s" % (key, `value`) for key, value in self.fieldValues.items()))
        
    @classmethod
    def create(cls):
        cls.conn().execute(cls._buildCreateQuery())
        cls._hasManyCreation()
        
    @classmethod
    def _buildCreateQuery(cls):
     
        template = '''create table if not exists %s (%s %s)'''
        if cls.key_name:
            keyDefinition = '%s integer primary key asc' % cls.key_name
            if cls.key_autoinc:
                keyDefinition += ' autoincrement'
            keyDefinition += ','
        else:
            keyDefinition = ''
        fieldDefinition = []
        for name, pyType in cls.fieldTypes.items():
            if name != cls.key_name:
                if pyType in cls.sqlMapping:
                    sqlType = cls.sqlMapping[pyType]
                elif isinstance(pyType, DataBaseType):
                    sqlType = 'TEXT'
                else:
                    raise DataBaseException("Cannot store %s in SQL" % repr(pyType))
                fieldD = '%s %s' % (name, sqlType)
                if cls.fieldUniques[name]:
                    fieldD += ' unique'
                fieldDefinition.append(fieldD)
        fieldDefinition = ', '.join(fieldDefinition)

        return template % (cls.__name__, keyDefinition, fieldDefinition)

    @classmethod
    def _hasManyCreation(cls):
        for ref in cls.has_many:
            template = '''create table if not exists %s (%s, %s)'''
            tableName = cls.__name__ + "_to_" + ref.__name__
            clsID = "%s_id integer" % (cls.__name__)
            refID = "%s_id integer" % (ref.__name__)
            query = template % (tableName, clsID, refID)
            cls.conn().execute(query)
            

    @classmethod
    def fromSQL(cls, id):
        conn = cls.conn()
        query = "select * from %s where %s=?"
        query = query % (cls.__name__, cls.key_name)
        result = conn.execute(query, (id,))
        row = list(result)[0]

        inst = cls()
        for name in cls.fieldTypes:
            inst.fieldValues[name] = row[name]
            
        return inst
        
    @classmethod
    def fromAttrs(cls, **attrs):
        inst = cls()
        for name in cls.fieldTypes:
            if name in attrs:
                inst.fieldValues[name] = attrs[name]
        return inst
        
    @classmethod
    def _iter_wrapper(cls):
        query = "select * from %s" % cls.__name__
        for row in cls.conn().execute(query):
            yield cls.fromAttrs(**row)
            
    @classmethod
    def select(cls, **dct):
        for inst in cls:
            for name, value in dct.items():
                if inst.fieldValues[name] == value:
                    yield inst
                    
    @classmethod
    def select_re(cls, **dct):
        for inst in cls:
            for name, value in dct.items():
                if re.match(value, inst.fieldValues[name]):
                    yield inst        
    
    @classmethod
    def select_cond(cls, cond, values = tuple()):
        value_list = []
        for val in values:
            try:
                val = val.decode('utf-8')
            except:
                pass
            value_list.append(val)

        query = u"select * from %s where %s" % (cls.__name__, cond)
        for row in cls.conn().execute(query, tuple(value_list)):
            yield cls.fromAttrs(**row)

    @classmethod
    def select_id(cls, id):
        query = "select * from %s where %s=?" % (cls.__name__, cls.key_name)
        return cls.fromAttrs(**list(cls.conn().execute(query, (id,)))[0])
        #for row in cls.conn().execute(query,(id,)):
            #yield cls.fromAttrs(**row)
            
    @classmethod
    def hasMany(cls, ref, alias=""):
        if not issubclass(ref, DataBaseObj):
            raise DataBaseException("Reference %s is not a subclass of DataBaseObj!" % ref)
        cls.has_many.append(ref)
        if alias:
            cls.ref_alias[alias] = ref
        ref.belongs_to.append(cls)
        
    @classmethod
    def hasA(cls, ref, alias=""):
        if not issubclass(ref, DataBaseObj):
            raise DataBaseException("Reference %s is not a subclass of DataBaseObj!" % ref)
        cls.has_many.append(ref)
        cls.singular_refs.append(ref)
        if alias:
            cls.ref_alias[alias] = ref
        ref.belongs_to.append(cls)
        
    @classmethod
    def count(cls):
        template = '''select count(*) from %s'''
        tableName = cls.__name__
        query = template % tableName
        return list(cls.conn().execute(query))[0][0]

    @classmethod
    def count_cond(cls, cond, values = tuple()):
        template = '''select count(*) from %s where %s'''
        tableName = cls.__name__
        query = template % (tableName, cond)
        return list(cls.conn().execute(query, values))[0][0]


    @classmethod
    def get_by(cls, **kwargs):
        cond = ' and '.join('%s = ?' % key for key in kwargs.keys())
        values = tuple(kwargs.values())
        try:
            return cls.select_cond(cond, values).next()
        except StopIteration:
            return None

    @classmethod
    def select_sort(cls, row, asc=True, cond = "", limit="", offset="", values = tuple()):
        if asc:
            d = "asc"
        else:
            d = "desc"
        if cond != "":
            cond = "where %s" % cond
        if limit != "":
            limit = "limit %s" % limit
        if offset != "":
            offset = "offset %s" % offset
        query = "select * from %s %s order by %s %s %s %s" % (cls.__name__, cond, row, d, limit, offset)
        try:
            for row in cls.conn().execute(query, values):
                yield cls.fromAttrs(**row)
        except Exception, e:
            print query
            print e
            
    
    @classmethod 
    def select_creation(cls, asc=True, cond = "", limit="", offset="", values = tuple()):
        for inst in cls.select_sort("cdate", asc, cond, limit, offset, values):
            yield inst


    @classmethod
    def wrap_sql(cls, rows):
        for row in rows:
            yield cls.fromAttrs(**row)

    @classmethod
    def objects(cls):
        table_name = cls.__name__
        stmt = SelectStatement(table_name, proxy=cls, conn=cls.conn())
        return stmt


if __name__ == "__main__":
    
    import datetime, time

    def isEmail(value):
        if len(value.split("@")) == 2:
            return True
        else:
            return False


    class posts(DataBaseObj):
        
        hasField(int, "id")
        hasKey("id")
        hasField(str, "title")
        hasField(str, "text")


    class images(DataBaseObj):
        
        hasField(str, "size")
        hasField(str, "file")


    class users(DataBaseObj):
        
        hasField(str, "name")
        hasField(str, "email", unique=True, restrictor=isEmail)
        hasField(DataBaseArray(int), "testIntArray")
        hasMany(posts)
        hasA(images)
        hasField(DataBaseDate(), "joindate")


    import sqlite3
    conn = sqlite3.connect(":memory:")    
    globalConnObj = conn
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    users.create()
    posts.create()
    images.create()

    try:
        users.new(name="Paul Seidel", email="paul@pyttp.net", joindate=datetime.datetime.now())
        time.sleep(0.1)
        users.new(name="Ipsum Lorem", email="ipsum@pyttp.net")
        time.sleep(0.1)
        users.new(name="Python Guru", email="python@pyttp.net")
        time.sleep(0.1)
#        users.new(name="Bad Impostor", email="paul@pyttp.net")
    except sqlite3.IntegrityError:
        import traceback
        traceback.print_exc()
    
    for user in users.select_re(name="P.*"):
        print user.show()
    
    for user in users.select_cond("name > ?", ("J",)):
        print user.show()
        
    #arrayUser = user.new(name="Array User", email="arrayuser@pyttp.net")
    #try:
        #arrayUser.testIntArray = [1, 1337, 23, "foo"]
    #except:
        #import traceback
        #traceback.print_exc()
    
    print users.select_id(1).show()
    
    postUser = users.new(name="The Author", email="author@pyttp.net")
    aPost = posts.new(title="A new post", text="Once upon a time ...")
    anotherPost = posts.new(title="The other post", text="In a land far, far away ...")
    
    if not postUser.hasRef(aPost):    
        postUser.setRef(aPost)
    if not postUser.hasRef(aPost):
        postUser.setRef(aPost)
    postUser.setRef(anotherPost)
    
    postUser.deleteRef(anotherPost)

    for post in postUser.posts:
        print post.show()

    print "Before:".center(80)
    for user in users:
        print user.show()
    print
    users.delete(postUser, deleteRefs=[posts])
    
    print "After:".center(80)
    for user in users:
        print user.show()    
    print
    print "Posts:".center(80)
    for post in posts:
        print post.show()

    posts.delete(anotherPost)
    
    for user in anotherPost.users:
        print user.show()


    imgUser = users.new(name="I has a Image", email="image@pyttp.net")
    img1 = images.new(size="800x600", file="avatar.jpeg")

    img1 = images.get_by(size="800x600", file="avatar.jpeg")
    assert img1
    
    imgUser.setRef(img1)
    try:
        imgUser.setRef(img1)
    except:
        print "Image already set"


    newUser = users.new(name="The new One", testIntArray=[1,2,3,4], email="noob@idk.net")
    print newUser.show()
    
    print users.count()
    print users.count_cond("name > ? and name < ?", ("P", "Q"))
    print users.count_cond("name > 'P'")
    
    print "joindate".center(80, "=")
    
    for user in users.select_sort("joindate", asc=False):
        print user.show()

    print "cdate".center(80, "=")
    for user in users.select_creation(asc=False, limit=2):
        print user.show()