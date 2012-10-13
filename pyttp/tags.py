
from pyttp.database import DataBaseObj, hasField


class TagRegistry(object):

    REGISTRY = None


    def __init__(self):
        self.cls_lookup = dict()
        self.spec_lookup = dict()


    @classmethod
    def register(cls, cls_obj, cls_spec):
        cls._init_registry()
        cls.REGISTRY.cls_lookup[cls_spec] = cls_obj
        cls.REGISTRY.spec_lookup[cls_obj] = cls_spec


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


def is_tagged(cls_spec):
    def decorator(cls):
        TagRegistry.register(cls, cls_spec)
        return cls
    return decorator



class Tag(DataBaseObj):
    hasField(unicode, "name")
    hasField(int, "obj_id")
    hasField(unicode, "cls_spec")

    @classmethod
    def get_objs_by_name(cls, name, cls_spec=None):
        if cls_spec:
            obj_ids = [x.obj_id for x in cls.select_cond("name = ? and cls_spec = ?", (name, cls_spec))]
            cls_obj = TagRegistry.get_cls(cls_spec)
            assert cls_obj
            for obj_id in obj_ids:
                yield cls_obj.select_id(obj_id)
        else:
            tag_objs = cls.select_cond("name = ?", (name,))
            for tag in tag_objs:
                cls_obj = TagRegistry.get_cls(tag.cls_spec)
                assert cls_obj
                yield cls_obj.select_id(tag.obj_id)


    @classmethod
    def get_tag_cloud(cls, cls_spec=None, limit=None):
        if cls_spec:
            tags = cls.select_cond("cls_spec = ?", (cls_spec,))
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
    try:
        tag = Tag.select_cond("name = ? and cls_spec = ? and obj_id = ?", (name, cls_spec, obj.id)).next()
        Tag.delete(tag)
    except StopIteration:
        pass


def set_tags(obj, tag_line):
    assert obj.id
    cls_spec = TagRegistry.get_spec(obj.__class__)
    assert cls_spec
    current_tags = set(tag.name for tag in
                      Tag.select_cond("cls_spec = ? and obj_id = ?", (cls_spec, obj.id)))
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
    current_tags = list(Tag.select_cond("cls_spec = ? and obj_id = ?", (cls_spec, obj.id)))
    return current_tags


def get_tag_line(obj):
    return ', '.join(tag.name for tag in get_tags(obj))

