from flask import Blueprint

hello_page = Blueprint('blueprint_name_for_hello_page', __name__)

@hello_page.route('/databot/hello')

def hello_world():
	return 'Hello World!'