
class Paginator(object):

    class InvalidPageError(Exception):
        pass

    def __init__(self, objects, page=1, items_per_page=10):
        self._objects = objects
        self.items_per_page = items_per_page
        self.page = page

    @property
    def objects(self):
        offset = self.items_per_page * (self.page - 1)
        return self._objects[offset:offset + self.items_per_page]

    @property
    def count(self):
        return len(self._objects)

    @classmethod
    def get_page(cls, request, page_parameter=None):
        page_parameter = page_parameter or 'page'
        try:
            page = int(request.REQUEST.get(page_parameter, 1))
            if page < 1:
                raise cls.InvalidPageError
        except ValueError:
            raise cls.InvalidPageError

        return page


def paginate(objects_key, items_per_page=10, page_parameter=None):
    def decorate(meth):

        def inner(inst, request, *args, **kwargs):
            response = meth(inst, request, *args, **kwargs)
            objects = response.context[objects_key]

            try:
                page = Paginator.get_page(request, page_parameter)
            except Paginator.InvalidPageError:
                page = 1
            paginator = Paginator(objects, page, items_per_page)

            response.context[objects_key] = paginator
            return response

        return inner
    return decorate
