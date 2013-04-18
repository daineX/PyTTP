from unittest import TestCase

from pyttp.sql_statements import SelectStatement


class SQLStatementsTests(TestCase):

    def test_columns(self):
        stmt = (SelectStatement("user")
                    .columns("id", "first_name", "city", "birth_date"))
        self.assertEqual(unicode(stmt), "SELECT id, first_name, city, birth_date FROM user;")

    def test_filter(self):
        stmt = (SelectStatement("user")
                    .filter(first_name="Paul", age=32))
        self.assertEqual(unicode(stmt), "SELECT * FROM user WHERE first_name = ? AND age = ?;")
        self.assertEqual(stmt._values(), ["Paul", 32])

    def test_order_by(self):
        stmt = SelectStatement("user").order_by("first_name")
        self.assertEqual(unicode(stmt), "SELECT * FROM user ORDER BY first_name;")

    def test_compare_op(self):
        stmt = SelectStatement("user").filter(age__gt=18)
        self.assertEqual(unicode(stmt), "SELECT * FROM user WHERE age > ?;")
        self.assertEqual(stmt._values(), [18])

    def test_limit(self):
        stmt = SelectStatement("user").filter(age__gt=18).limit(10)
        self.assertEqual(unicode(stmt), "SELECT * FROM user WHERE age > ? LIMIT 10;")
        self.assertEqual(stmt._values(), [18])

    def test_in(self):
        stmt = SelectStatement("user").filter(first_name__in=["Paul", "Hans", ])
        self.assertEqual(unicode(stmt), "SELECT * FROM user WHERE first_name IN (?,?);")
        self.assertEqual(stmt._values(), ["Paul", "Hans"])

    def test_join(self):
        stmt = SelectStatement("user").join("address", user_id="id")
        self.assertEqual(unicode(stmt), "SELECT * FROM user JOIN address ON address.user_id = user.id;")

    def test_bool_op(self):
        stmt = (SelectStatement("user")
                    .filter(first_name="Hans")
                    .filter(or__city__eq="Berlin")
                )
        self.assertEqual(unicode(stmt), "SELECT * FROM user WHERE first_name = ? OR city = ?;")
        self.assertEqual(stmt._values(), ["Hans", "Berlin"])

    def test_complex(self):
        stmt = (SelectStatement("user")
                    .join("address", id="address_id")
                    .filter(country_code='de')
                    .filter(zip_code__gt=10000)
                    .filter(zip_code__lt=15000)
                    .filter(or__first_name__ne="Paul")
               )
        self.assertEqual(unicode(stmt), "SELECT * FROM user JOIN address ON address.id = user.address_id WHERE country_code = ? AND zip_code > ? AND zip_code < ? OR first_name != ?;")
