
class ValidationException(Exception):

    def __init__(self, msg):
        self.msg = msg


def not_empty(value):
    if not value:
        raise ValidationException("Please insert a value")
    return value


def is_email(email_str):
    if len(email_str.split("@")) != 2:
        raise ValidationException("Invalid email address")
    return email_str


def id_validator(model):
    def inner(value):
        try:
            model.select_id(int(value))
            return int(value)
        except:
            raise ValidationException("Invalid Id")
    return inner


def model_validator(model):
    def inner(value):
        try:
            return model.select_id(int(value))
        except:
            raise ValidationException("Invalid Id")
    return inner
