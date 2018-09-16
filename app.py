from __future__ import print_function
import os
from parse import upload_xml
from flask import Flask, request
from accounts import create_user, validate_user_id
import sys


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)




app = Flask('update_db')


@app.route('/', methods=['POST'])
def result():
    new_user = request.form.get('create_user')
    print(new_user)
    password = request.form.get('password')
    user_id = request.form.get('user_id')
    if any(x is None for x in [password,user_id]):
        return '\nYou need to enter a user_id and password, ' \
               'or create a new user with:\n\n' \
               'curl -X POST -F user_id=your_username -F password=your_password -F create_user=true http://35.203.51.139/upload/ \n\n'

    print(request.form)
    if new_user:
        return create_user(user_id=user_id, password=password)

    if not validate_user_id(user_id=user_id, password=password):
        return '\nIncorrect user_id and password combo. ' \
               'Create a new user with:\n\n' \
               'curl -X POST -F user_id=your_username -F password=your_password -F create_user=true http://35.203.51.139/upload/ \n\n'



    file = request.files.get('file')

    if file:
        print('filename', file.filename, [method_name for method_name in dir(file)])
        upload_xml(file.read(), user_id)
        return '\nReceived {}\n\n'.format(file.filename)
    else:
        print('shit')


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port)
