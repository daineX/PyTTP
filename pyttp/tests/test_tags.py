import unittest

from pyttp import database as db
import sqlite3

from pyttp.tags import *


@is_tagged("tagged_obj")
class TaggedObject(db.DataBaseObj):
    hasField(unicode, "name")
    hasField(int, "number")


@is_tagged("another_tagged_obj")
class AnotherTaggedObject(db.DataBaseObj):
    hasField(unicode, "spam")
    hasField(int, "eggs")


class TagTests(unittest.TestCase):

    def setUp(self):
        conn = sqlite3.connect(":memory:")
        db.globalConnObj = conn
        conn.row_factory = sqlite3.Row
        TaggedObject.create()
        AnotherTaggedObject.create()
        Tag.create()

    def tearDown(self):
        for tag in Tag.objects().all():
            Tag.delete(tag)


    def test_set_tag(self):
        obj1 = TaggedObject(name="foo", number=1)
        obj1.save()
        obj2 = AnotherTaggedObject(spam="bla", eggs=4)
        obj2.save()
        set_tag(obj1, "bar")
        set_tag(obj2, "bar")

        tagged_objs = list(Tag.get_objs_by_name("bar"))
        self.assertTrue(obj1 in tagged_objs)
        self.assertTrue(obj2 in tagged_objs)


    def test_filter_objs_by_cls(self):
        obj1 = TaggedObject(name="foo", number=1)
        obj1.save()
        obj2 = AnotherTaggedObject(spam="bla", eggs=4)
        obj2.save()
        set_tag(obj1, "bar")
        set_tag(obj2, "bar")

        tagged_objs = list(Tag.get_objs_by_name("bar", cls_spec="tagged_obj"))
        self.assertTrue(obj1 in tagged_objs)
        self.assertFalse(obj2 in tagged_objs)


    def test_remove_tag(self):
        obj1 = TaggedObject(name="foo", number=1)
        obj1.save()
        set_tag(obj1, "bar")

        tagged_objs = list(Tag.get_objs_by_name("bar", cls_spec="tagged_obj"))
        self.assertTrue(obj1 in tagged_objs)

        remove_tag(obj1, "bar")

        tagged_objs = list(Tag.get_objs_by_name("bar", cls_spec="tagged_obj"))
        self.assertFalse(obj1 in tagged_objs)


    def test_set_tags(self):
        obj1 = TaggedObject(name="foo", number=1)
        obj1.save()

        set_tags(obj1, "test, debug, PyTTP")
        current_tags = get_tag_line(obj1)
        self.assertTrue("test" in current_tags)
        self.assertTrue("debug" in current_tags)
        self.assertTrue("PyTTP" in current_tags)

        set_tags(obj1, "test, html")
        current_tags = get_tag_line(obj1)
        self.assertTrue("test" in current_tags)
        self.assertTrue("html" in current_tags)
        self.assertFalse("debug" in current_tags)
        self.assertFalse("PyTTP" in current_tags)


    def test_tag_cloud(self):
        obj1 = TaggedObject(name="foo", number=1)
        obj1.save()
        set_tags(obj1, "test, debug, FIRE")

        obj2 = TaggedObject(name="bar", number=2)
        obj2.save()
        set_tags(obj2, "debug, FIRE")

        obj3 = TaggedObject(name="baz", number=3)
        obj3.save()
        set_tags(obj3, "debug")

        tag_cloud = Tag.get_tag_cloud(cls_spec="tagged_obj")

        self.assertEqual([("debug", 3), ("FIRE", 2), ("test", 1)], tag_cloud)
