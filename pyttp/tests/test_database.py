import unittest

import sys
sys.path.append("../..")

from pyttp import database as db
import sqlite3

def isEmail(value):
    if len(value.split("@")) == 2:
        return True
    else:
        return False

class posts(db.DataBaseObj):
    
    db.hasField(int, "id")
    db.hasKey("id")
    db.hasField(str, "title")
    db.hasField(str, "text")


class images(db.DataBaseObj):
    
    db.hasField(str, "size")
    db.hasField(str, "file")



class users(db.DataBaseObj):
    db.hasField(str, "name")
    db.hasField(str, "email", unique=True, restrictor=isEmail)
    db.hasField(db.DataBaseArray(int), "testIntArray")
    db.hasMany(posts)
    db.hasA(images, "avatar")
    db.hasField(db.DataBaseDate(), "joindate")


class TestDataBaseObjs(unittest.TestCase):
    
    def setUp(self):
        conn = sqlite3.connect(":memory:")    
        db.globalConnObj = conn
        conn.row_factory = sqlite3.Row
        users.create()
        images.create()
        posts.create()
        
    def testCreation(self):
        user1 = users.new(name="Ipsum Lorem", email="test1@test.com")
        self.assertEqual(users.count(), 1)
        user2 = users.new(name="Ipsum Lorems", email="test2@test.com")
        self.assertEqual(users.count(), 2)
        self.assertNotEqual(user1, user2)
        
    def testDeletion(self):
        users.new(name="Ipsum Lorem", email="test1@test.com")
        users.new(name="Ipsum Lorem", email="test2@test.com")
        users.new(name="Ipsum Lorem", email="test3@test.com")
        users.new(name="Ipsum Lorem", email="test4@test.com")
        self.assertEqual(users.count(), 4)
        for user in users:
            users.delete(user)
        self.assertEqual(users.count(), 0)
        
    def testUniques(self):
        users.new(name="A user", email="thisUsers@mail.com")
        self.assertRaises(sqlite3.IntegrityError, users.new, name="Another user", email="thisUsers@mail.com")
        
    def testRestrictor(self):
        self.assertRaises(db.DataBaseException, users.new, name="Invalid Email", email="this.is.no.valid")
        
    def testValue(self):
        theUser = users.new(name="A user", email="thisUsers1@mail.com")
        theUser.name = "a new name"
        self.assertEqual(theUser.name, "a new name")
        try:
            unknownValue = theUser.unknownField
            raise Exception("AttributeError was not raised!")
        except AttributeError:
            pass
        
    def testSetRef(self):
        imageUser = users.new(name="Image User", email="valid@email.org")
        theImage = images.new(size="800x600", file="imagefile.png")
        imageUser.setRef(theImage)
        self.assertTrue(imageUser.hasRef(theImage))
        
    def testDoubleSetRef(self):
        imageUser = users.new(name="Image User", email="valid@email.org")
        theImage = images.new(size="800x600", file="imagefile.png")
        imageUser.setRef(theImage)
        self.assertRaises(db.DataBaseException, imageUser.setRef, theImage)
        
    def testDeleteRef(self):
        imageUser = users.new(name="Image User", email="valid2@email.org")
        theImage = images.new(size="700x500", file="imagefile")
        imageUser.setRef(theImage)
        imageUser.deleteRef(theImage)
        self.assertEqual(list(imageUser.getRefs(images)), [])
        
    def testRefAlias(self):
        imageUser = users.new(name="Image User", email="valid2@email.org")
        theImage = images.new(size="700x500", file="imagefile")
        imageUser.setRef(theImage)
        
        self.assertEqual(theImage, imageUser.avatar)
        
    def testCastValue(self):
        theUser = users.new(name=int("42",0xd), email="valied3@emal.ir")
        self.assertEqual(theUser.name.__class__, str)
        self.assertEqual(theUser.name, "54")
        
    def testArray(self):
        arrayUser = users.new(name="Array User", email="array@users.org")
        theArray = range(10)
        arrayUser.testIntArray = theArray
        for i, item in enumerate(arrayUser.testIntArray):
            self.assertEqual(theArray[i], item)
            

        
if __name__ == "__main__":

    unittest.main()