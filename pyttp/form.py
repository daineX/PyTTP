
from itertools import chain
from copy import deepcopy
import string

from pyttp.html import html_escape

from pyttp.validators import ValidationException

class Field(object):

    default_validators = None

    def __init__(self, name=None, value=None, validators=None, required=True):
        self.name = name
        self.required = required
        if value is None:
            value = ''
        self.raw_value = value
        self._value = None
        if validators is None:
            validators = []
        if self.default_validators is not None:
            validators += self.default_validators
        self.validators = validators
        self.field = None
        self.errors = []

    def bool(self, value):
        return bool(value)

    def is_valid(self):
        value = self.raw_value
        if not self.bool(value) and not self.required:
            return True
        for validator in self.validators:
            try:
                value = validator(value)
            except ValidationException as e:
                self.errors.append(e.msg)
                return False
        self._value = value
        return True


    @property
    def value(self):
        if self._value is not None:
            return self._value
        else:
            return self.raw_value


    def render(self):
        raise NotImplementedError


    @property
    def id(self):
        return self.name


class TextField(Field):

    def render(self):
        return '<input name="%s" id="%s" type="text" value="%s" />' % (self.name, self.id, html_escape(self.raw_value))


class HiddenField(Field):

    def render(self):
        return '<input name="%s" id="%s" type="hidden" value="%s" />' % (self.name, self.id, html_escape(self.raw_value))


class TextAreaField(Field):

    def render(self):
        return '<textarea name="%s" id="%s">%s</textarea>' % (self.name, self.id,
            html_escape(self.raw_value))


class FileField(Field):

    def render(self):
        return '<input name="%s" id="%s" type="file" />' % (self.name, self.id)

    def bool(self, value):
        return getattr(value, 'filename', False)


class PasswordField(Field):

    def render(self):
        return '<input name="%s" id="%s" type="password" />' % (self.name, self.id)


class Bunch(dict):

    def __getattr__(self, value):
        try:
            return self.__getitem__(value)
        except:
            raise AttributeError(value)


    def __setattr__(self, name, value):
        self.__setitem__(name, value)


class Form(object):

    def __init__(self, kwargs=None):
        self.has_values = bool(kwargs)
        self.fields = Bunch()
        for name, field in self._get_fields():
            inst_field = deepcopy(field)
            if kwargs and name in kwargs:
                inst_field.raw_value = kwargs[name]
            inst_field.form = self
            inst_field.name = name
            self.fields[name] = inst_field
        self._name = None


    @property
    def name(self):
        if self._name:
            return self._name
        self._name = self.__class__.__name__.lower()
        return self._name


    def _get_fields(self):
        for name in self.__class__.__dict__:
            inst = self.__class__.__dict__[name]
            if isinstance(inst, Field):
                yield name, inst


    def is_valid(self):
        all_valid = [field.is_valid() for field in self.fields.values()]
        return all(all_valid)

    @property
    def errors(self):
        return {name: field.errors for name, field in self.fields.items()}
