import sqlite3


global_connection = None
debug = False

def get_connection():
    return global_connection

def connect(params):
    conn = sqlite3.connect(params)
    conn.row_factory = sqlite3.Row
    global_connection = connect


class SQLStatement(object):

    def __init__(self, proxy=None, conn=None):
        self.proxy = proxy
        if conn:
            self.conn = conn
        else:
            self.conn = get_connection()

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
        return self.conn.execute(query, tuple(values))


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

    def __init__(self, table_name, proxy=None, conn=None):
        super(WhereStatement, self).__init__(proxy=proxy, conn=conn)
        self.table_name = table_name
        self.filters = []


    def _where_statement(self):
        if self.filters:
            where_statement = u"WHERE " + u" AND ".join(u"{}=?".format(key) for key, value in self.filters)
        else:
            where_statement = u""
        return where_statement


    def filter(self, **kwargs):
        for key, value in kwargs.items():
            self.filters.append((key, value))
        return self


    def _values(self):
        return [value for key, value in self.filters]        


class SelectStatement(WhereStatement):

    TEMPLATE = u"""SELECT {columns_statement} FROM {table_name} {join_statement} {where_statement} {order_by_statement} {limit_statement} {offset_statement};"""
    ON_TEMPLATE = u"{join_table}.{join_on} = {table_name}.{table_on}"

    def __init__(self, table_name, proxy=None, conn=None):
        super(SelectStatement, self).__init__(table_name, proxy=proxy, conn=conn)
        self.order_by_column = None
        self.limit_amount = None
        self.offset_amount = None
        self.selected_columns = []
        self.join_list = []
        self.ascending = False
        self.descending = False
        


    def _on_statement(self, join_table, on):
        assert len(on.items()) == 1
        join_on, table_on = on.items()[0]
        return self.ON_TEMPLATE.format(join_table=join_table,
                                       join_on=join_on,
                                       table_name=self.table_name,
                                       table_on=table_on)


    def _join_statement(self):
        return " ".join(u"JOIN {table_name} ON {on}".format(table_name=join_table,
                                                            on=self._on_statement(join_table, on))
                        for join_table, on in self.join_list)


    def _order_by_statement(self):
        if self.order_by_column:
            order_by_statement = u"ORDER BY {}".format(self.order_by_column)
        else:
            order_by_statement = u""
        if self.ascending:
            order_by_statement += " ASC"
        elif self.descending:
            order_by_statement += " DESC"
        return order_by_statement


    def _build_query(self):


        if self.limit_amount is not None:
            limit_statement = u"LIMIT {amount}".format(amount=self.limit_amount)
        else:
            limit_statement = u""
        if self.offset_amount is not None:
            offset_statement = u"OFFSET {amount}".format(amount=self.offset_amount)
        else:
            offset_statement = u""
        if self.selected_columns:
            columns_statement = u", ".join(self.selected_columns)
        else:
            columns_statement = u"*"
        join_statement = self._join_statement()
        return self.TEMPLATE.format(table_name=self.table_name,
                                    where_statement=self._where_statement(),
                                    order_by_statement=self._order_by_statement(),
                                    limit_statement=limit_statement,
                                    offset_statement=offset_statement,
                                    columns_statement=columns_statement,
                                    join_statement=join_statement).strip()


    def columns(self, *args):
        self.selected_columns = args
        return self


    def order_by(self, column):
        self.order_by_column = column
        return self


    def limit(self, amount):
        self.limit_amount = amount
        return self


    def offset(self, amount):
        self.offset_amount = amount
        return self


    def join(self, table_name, **on):
        self.join_list.append((table_name, on))
        return self


    def asc(self):
        self.ascending = True
        return self


    def desc(self):
        self.descending = True
        return self


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
        self.conn.execute(raw, values)


if __name__ == "__main__":
    stmt = SelectStatement("user").columns("id", "first_name", "city", "birth_date")
    stmt = stmt.filter(first_name="Paul", city="Berlin").order_by("id").limit(10)
    stmt = stmt.join("posts", user_id="id")
    print stmt._build_query()
    print stmt._values()

    stmt = InsertStatement("user").columns("first_name", "city").values("Paul", "Berlin")
    print stmt._build_query()

    stmt = UpdateStatement("user")
    stmt.filter(id=10).values(first_name="Paul", city="Berlin")
    print stmt._build_query()
    print stmt._values()
