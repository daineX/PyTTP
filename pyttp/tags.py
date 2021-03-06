import re
from functools import partial
from pyttp.database import DataBaseObj, hasField


class TagRegistry(object):

    REGISTRY = None


    def __init__(self):
        self.cls_lookup = dict()
        self.spec_lookup = dict()


    @staticmethod
    def _cls_spec_from_name(name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @classmethod
    def register(cls, cls_obj, cls_spec=None):
        if cls_spec is None:
            cls_spec = cls._cls_spec_from_name(cls_obj.__name__)
        cls._init_registry()
        cls.REGISTRY.cls_lookup[cls_spec] = cls_obj
        cls.REGISTRY.spec_lookup[cls_obj] = cls_spec

        cls_obj.get_objs_by_tag_name = partial(Tag.get_objs_by_name, cls_spec=cls_spec)
        cls_obj.get_objs_by_tag_names = partial(Tag.get_objs_by_names, cls_spec=cls_spec)
        cls_obj.get_tag_cloud = partial(Tag.get_tag_cloud, cls_spec=cls_spec)

        cls_obj.get_tag_line = get_tag_line
        cls_obj.get_tags = get_tags
        cls_obj.set_tags = set_tags
        cls_obj.set_tag = set_tag
        cls_obj.remove_tag = remove_tag


    @classmethod
    def _init_registry(cls):
        if cls.REGISTRY is None:
            cls.REGISTRY = cls()


    @classmethod
    def get_cls(cls, cls_spec):
        cls._init_registry()
        return cls.REGISTRY.cls_lookup.get(cls_spec)


    @classmethod
    def get_spec(cls, cls_obj):
        cls._init_registry()
        return cls.REGISTRY.spec_lookup.get(cls_obj)


def is_tagged(cls_spec=None):
    def decorator(cls):
        TagRegistry.register(cls, cls_spec=cls_spec)
        return cls
    return decorator



class Tag(DataBaseObj):
    hasField(unicode, "name")
    hasField(int, "obj_id")
    hasField(unicode, "cls_spec")

    @classmethod
    def get_objs_by_name(cls, name, cls_spec=None):
        if cls_spec:
            obj_ids = [x.obj_id for x in cls.objects().filter(name=name, cls_spec=cls_spec).all()]
            cls_obj = TagRegistry.get_cls(cls_spec)
            assert cls_obj
            for obj in cls_obj.objects().filter(id__in=obj_ids).all():
                yield obj
        else:
            tag_objs = cls.objects().filter(name=name).all()
            for tag in tag_objs:
                cls_obj = TagRegistry.get_cls(tag.cls_spec)
                assert cls_obj
                yield cls_obj.objects().filter(id=tag.obj_id).first()


    @classmethod
    def get_objs_by_names(cls, names, cls_spec=None):
        if cls_spec:
            query = cls.objects()
            for name in names:
                query = query.filter(or__name__eq=name, cls_spec=cls_spec)
            obj_ids = [x.obj_id for x in query.all()]
            cls_obj = TagRegistry.get_cls(cls_spec)
            assert cls_obj
            for obj in cls_obj.objects().filter(id__in=obj_ids).all():
                yield obj
        else:
            query = cls.objects()
            for name in names:
                query = query.filter(or__name__eq=name)
            tag_objs = query.all()
            for tag in tag_objs:
                cls_obj = TagRegistry.get_cls(tag.cls_spec)
                assert cls_obj
                yield cls_obj.objects().filter(id=tag.obj_id).first()


    @classmethod
    def get_tag_cloud(cls, cls_spec=None, limit=None):
        if cls_spec:
            tags = cls.objects().filter(cls_spec=cls_spec).all()
        else:
            tags = list(cls)

        counts = {}
        for tag in tags:
            if tag.name in counts:
                counts[tag.name] += 1
            else:
                counts[tag.name] = 1

        counts = sorted([(tag, count) for tag, count in counts.items()], key= lambda x: x[1], reverse=True)
        if limit:
            counts = counts[:limit]
        return counts


def set_tag(obj, name):
    assert obj.id
    cls_spec = TagRegistry.get_spec(obj.__class__)
    assert cls_spec
    tag = Tag(name=name, obj_id=obj.id, cls_spec=cls_spec)
    tag.save()


def remove_tag(obj, name):
    cls_spec = TagRegistry.get_spec(obj.__class__)
    assert cls_spec
    tag = Tag.objects().filter(name=name, cls_spec=cls_spec, obj_id=obj.id).first()
    if tag:
        Tag.delete(tag)


def set_tags(obj, tag_line):
    assert obj.id
    cls_spec = TagRegistry.get_spec(obj.__class__)
    assert cls_spec
    current_tags = set(tag.name for tag in
                       Tag.objects().filter(cls_spec=cls_spec, obj_id=obj.id).all())
    tags_to_set = set([x.strip() for x in tag_line.split(",")])
    tags_to_delete = current_tags - tags_to_set
    tags_to_set = tags_to_set - current_tags

    for tag_name in tags_to_delete:
        remove_tag(obj, tag_name)
    for tag_name in tags_to_set:
        set_tag(obj, tag_name)


def get_tags(obj):
    cls_spec = TagRegistry.get_spec(obj.__class__)
    assert cls_spec
    current_tags = list(Tag.objects().filter(cls_spec=cls_spec, obj_id=obj.id).all())
    return current_tags


def get_tag_line(obj):
    return ', '.join(tag.name for tag in get_tags(obj))

