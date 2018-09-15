from db_utils import mongo_decorator
from pymongo.errors import DuplicateKeyError


@mongo_decorator
def create_user(db=None, user_id=None, password=None):
    record = {'user_id': user_id,
              'password': password}
    try:
        update = db.accounts.insert(record)
        print(update)
        return '\nNew user {} added \n\n'.format(user_id)
    except DuplicateKeyError:
        return "\nThat user_id already exists!\n\n"


@mongo_decorator
def validate_user_id(db=None, user_id=None, password=None):
    record = {'user_id': user_id,
              'password': password}
    if db.accounts.find_one(record):
        print('user validated')
        return True
    return False
