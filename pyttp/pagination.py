
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
            page = int(request.REQUEST.get(page_parameter, 0))
            if page < 1:
                raise cls.InvalidPageError
        except ValueError:
            raise cls.InvalidPageError

        return page
