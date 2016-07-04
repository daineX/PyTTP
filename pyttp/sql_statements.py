import sqlite3
import copy

global_connection = None
debug = True

def get_connection():
    return global_connection

def connect(params):
    conn = sqlite3.connect(params)
    conn.row_factory = sqlite3.Row
    global_connection = conn

def return_copy(meth):
    def inner(inst, *args, **kwargs):
        copy_inst = copy.copy(inst)
        return meth(copy_inst, *args, **kwargs)
    return inner


class SQLStatement(object):

    def __init__(self, proxy=None, conn=None):
        self.proxy = proxy
        if conn:
            self.connection = conn
        else:
            self.connection = get_connection()

    def _values(self):
        raise NotImplementedError

    def _build_query(self):
        raise NotImplementedError

    def execute(self):
        query = self._build_query()
        if debug:
            print "QUERY:", query
        values = self._values()
        if debug:
            print "VALUES:", values
        return self.connection.execute(query, tuple(values))

    def proxy_execute(self):
        assert self.proxy
        return self.proxy.wrap_sql(self.execute())

    def all(self):
        return self.proxy_execute()

    def first(self):
        try:
            return self.proxy.wrap_sql(self.execute()).next()
        except StopIteration:
            return None


class WhereStatement(SQLStatement):

    OP_MAP = {'eq': '=',
              'ne': '!=',
              'gt': '>',
              'lt': '<',
              'ge': '>=',
              'le': '<=',
              'in': 'IN',
              'nin': 'NOT IN',
              'like': 'LIKE',
              'ilike': 'ILIKE'}

    BOOL_OPS = {'or': 'OR',
                'and': 'AND'}

    def __init__(self, table_name, proxy=None, conn=None):
        super(WhereStatement, self).__init__(proxy=proxy, conn=conn)
        self.table_name = table_name
        self.filters = []

    def _where_statement(self):
        if self.filters:
            where_statement = [" WHERE"]
            for index, data in enumerate(self.filters):
                (table_name, key, value, bool_op, op) = data
                if table_name is not None:
                    key = "{}.{}".format(table_name, key)
                if index:
                    where_statement.append(" {}".format(bool_op))
                where_statement.append(" {} {}".format(key, op))
                if op == "IN":
                    where_statement.append(" ({})".format(
                                                   ','.join("?" for _ in value)))
                else:
                    where_statement.append(" ?")
            return "".join(where_statement)
        else:
            return ""
        return where_statement

    def _parse_filter_op(self, key):
        table_count = key.count("___")
        table_name = None
        if table_count:
            table_name, key = key.split("___")
        split_count = key.count("__")
        key = key.split("__", split_count)
        if len(key) < 2:
            key = key + ["="]
        if len(key) < 3:
            key = ["AND"] + key
        bool_op, key, op = key
        op = self.OP_MAP.get(op, "=")
        bool_op = self.BOOL_OPS.get(bool_op, "AND")
        return table_name, bool_op, key, op

    @return_copy
    def filter(self, **kwargs):
        for key, value in kwargs.items():
            table_name, bool_op, key, op = self._parse_filter_op(key)
            self.filters.append((table_name, key, value, bool_op, op))
        return self

    def _values(self):
        vals = []
        for _, _, val, _, _ in self.filters:
            if isinstance(val, list):
                vals += val
            else:
                vals.append(val)
        return vals


class SelectStatement(WhereStatement):

    TEMPLATE = u"""SELECT {columns_statement} FROM {table_name}{join_statement}{where_statement}{order_by_statement}{limit_statement}{offset_statement};"""
    ON_TEMPLATE = u"{join_table}.{join_on} = {table_on}"

    def __init__(self, table_name, proxy=None, conn=None):
        super(SelectStatement, self).__init__(table_name, proxy=proxy, conn=conn)
        self.order_by_column = None
        self.limit_amount = None
        self.offset_amount = None
        self.selected_columns = []
        self.join_list = []
        self.ascending = False
        self.descending = False
        self.count_ = False

    def _on_statement(self, join_table, on):
        assert len(on.items()) == 1
        join_on, table_on = on.items()[0]
        return self.ON_TEMPLATE.format(join_table=join_table,
                                       join_on=join_on,
                                       table_on=table_on)

    def _join_statement(self):
        if self.join_list:
            return " " + " ".join(u"JOIN {table_name} ON {on}"
                                    .format(table_name=join_table,
                                            on=self._on_statement(join_table, on))
                             for join_table, on in self.join_list)
        else:
            return ""

    def _order_by_statement(self):
        if self.order_by_column:
            order_by_statement = u" ORDER BY {}".format(self.order_by_column)
        else:
            order_by_statement = u""
        if self.ascending:
            order_by_statement += " ASC"
        elif self.descending:
            order_by_statement += " DESC"
        return order_by_statement

    def _columns_statement(self):
       if self.selected_columns:
            columns_statement = u", ".join(self.selected_columns)
       else:
            columns_statement = u"*"
       if self.count_:
           return u"count({})".format(columns_statement)
       else:
           return columns_statement

    def _build_query(self):
        if self.limit_amount is not None:
            limit_statement = u" LIMIT {amount}".format(amount=self.limit_amount)
        else:
            limit_statement = u""
        if self.offset_amount is not None:
            offset_statement = u" OFFSET {amount}".format(amount=self.offset_amount)
        else:
            offset_statement = u""
        columns_statement = self._columns_statement()
        join_statement = self._join_statement()
        return self.TEMPLATE.format(table_name=self.table_name,
                                    where_statement=self._where_statement(),
                                    order_by_statement=self._order_by_statement(),
                                    limit_statement=limit_statement,
                                    offset_statement=offset_statement,
                                    columns_statement=columns_statement,
                                    join_statement=join_statement).strip()

    @return_copy
    def columns(self, *args):
        self.selected_columns = args
        return self

    @return_copy
    def order_by(self, column):
        self.order_by_column = column
        return self

    @return_copy
    def limit(self, amount):
        self.limit_amount = amount
        return self

    @return_copy
    def offset(self, amount):
        self.offset_amount = amount
        return self

    @return_copy
    def join(self, table_name, **on):
        self.join_list.append((table_name, on))
        return self

    @return_copy
    def asc(self):
        self.ascending = True
        return self

    @return_copy
    def desc(self):
        self.descending = True
        return self

    @return_copy
    def count(self):
        self.count_ = True
        return iter(self.execute()).next()[0]

    @return_copy
    def __getitem__(self, slice_):
        if isinstance(slice_, slice):
            if slice_.start is not None:
                self.offset_amount = slice_.start
            if slice_.stop is not None:
                if slice_.start is None:
                    self.limit_amount = slice_.stop
                else:
                    self.limit_amount = slice_.stop - slice_.start
        else:
            self.offset_amount = slice_
            self.limit_amount = 1
        return self

    def __len__(self):
        return self.count()

    def __iter__(self):
        return iter(self.all())

    def __unicode__(self):
        return self._build_query()

class InsertStatement(SQLStatement):

    INSERT_TEMPLATE = u"INSERT INTO {table_name} ({columns}) VALUES ({values});"

    def __init__(self, table_name, proxy=None, conn=None):
        super(InsertStatement, self).__init__(proxy=proxy, conn=conn)
        self.table_name = table_name
        self.insert_columns = []
        self.insert_values = []

    def _values_statement(self):
        return ', '.join('?' for _ in self._values())

    def _columns_statement(self):
        return ', '.join(self.insert_columns)

    def _build_query(self):
        return self.INSERT_TEMPLATE.format(table_name=self.table_name,
                                           columns=self._columns_statement(),
                                           values=self._values_statement())

    def columns(self, *args):
        self.insert_columns.extend(args)
        return self

    def values(self, *args):
        self.insert_values.extend(args)
        return self

    def _values(self):
        return self.insert_values


class UpdateStatement(WhereStatement):

    UPDATE_TEMPLATE = u"UPDATE {table_name} SET {values} {where_statement};"

    def __init__(self, table_name, proxy=None, conn=None):
        super(UpdateStatement, self).__init__(table_name, proxy=proxy, conn=conn)
        self.update_values = []

    def _value_statement(self):
        return ", ".join("{} = ?".format(key) for key, value in self.update_values)

    def _build_query(self):
        return self.UPDATE_TEMPLATE.format(table_name=self.table_name,
                                           values=self._value_statement(),
                                           where_statement=self._where_statement())

    def values(self, **qargs):
        for key, value in qargs.items():
            self.update_values.append((key, value))
        return self

    def _values(self):
        return ([value for key, value in self.update_values] +
                super(UpdateStatement, self)._values())


class RawStatement(SQLStatement):

    def __init__(self, proxy=None, conn=None):
        super(RawStatement, self).__init__(proxy=proxy, conn=conn)

    def execute(self, raw, *values):
        self.connection.execute(raw, values)

