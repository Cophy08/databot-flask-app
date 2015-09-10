from flask import Blueprint

bye_page = Blueprint('blueprint_name_for_bye_page', __name__)

@bye_page.route('/databot/bye')

def bye_world():
	return 'Bye World!'