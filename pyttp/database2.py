import sqlite3


global_connection = None


def get_connection():
    return global_connection

def connect(params):
    conn = sqlite3.connect(params)
    conn.row_factory = sqlite3.Row
    global_connection = connect


class SelectStatement(object):

    TEMPLATE = """SELECT {columns_statement} FROM {table_name} {where_statement} {order_by_statement} {limit_statement};"""

    def __init__(self, table_name, conn=None):
        self.table_name = table_name
        if conn:
            self.conn = conn
        else:
            self.conn = get_connection()

        self.filters = []
        self.order_by_column = None
        self.limit_amount = None
        self.selected_columns = []


    def execute(self):
        query = self.build_query()
        values = self.filters.values()
        return self.conn.execute(query, tuple(values))


    def build_query(self):
        if self.filters:
            where_statement = "WHERE " + " AND ".join("{}=?".format(key) for key, value in self.filters)
        else:
            where_statement = ""
        if self.order_by_column:
            order_by_statement = "ORDER BY {}".format(self.order_by_column)
        else:
            order_by_statement = ""
        if self.limit is not None:
            limit_statement = "LIMIT {amount}".format(amount=self.limit_amount)
        else:
            limit_statement = ""
        if self.selected_columns:
            columns_statement = ", ".join(self.selected_columns)
        else:
            columns_statement = "*"
        return self.TEMPLATE.format(table_name=self.table_name,
                                    where_statement=where_statement,
                                    order_by_statement=order_by_statement,
                                    limit_statement=limit_statement,
                                    columns_statement=columns_statement)


    def columns(self, *args):
        self.selected_columns = args
        return self


    def filter(self, **kwargs):
        for key, value in kwargs.items():
            self.filters.append((key, value))
        return self


    def order_by(self, column):
        self.order_by_column = column
        return self


    def limit(self, amount):
        self.limit_amount = amount
        return self

    def values(self):
        return [value for key, value in self.filters]

if __name__ == "__main__":
    stmt = SelectStatement("user").columns("id", "first_name", "city", "birth_date")
    stmt = stmt.filter(first_name="Paul", city="Berlin").order_by("id").limit(10)
    print stmt.build_query()
    print stmt.values()

