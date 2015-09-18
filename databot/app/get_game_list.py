from flask import Blueprint
from flask import request
from pprint import pprint
from datetime import datetime, timedelta
import pymysql
import json
import datetime

# dbconfig.py contains db access credentials
import dbconfig

#
#
# Cross-domain decorator - this can be removed when hosted publicly
# http://flask.pocoo.org/snippets/56/
#
#

from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper

def crossdomain(origin=None, methods=None, headers=None,
				max_age=21600, attach_to_all=True,
				automatic_options=True):

	if methods is not None:
		methods = ", ".join(sorted(x.upper() for x in methods))
	if headers is not None and not isinstance(headers, basestring):
		headers = ", ".join(x.upper() for x in headers)
	if not isinstance(origin, basestring):
		origin = ", ".join(origin)
	if isinstance(max_age, timedelta):
		max_age = max_age.total_seconds()

	def get_methods():
		if methods is not None:
			return methods

		options_resp = current_app.make_default_options_response()
		return options_resp.headers["allow"]

	def decorator(f):
		def wrapped_function(*args, **kwargs):
			if automatic_options and request.method == "OPTIONS":
				resp = current_app.make_default_options_response()
			else:
				resp = make_response(f(*args, **kwargs))
			if not attach_to_all and request.method != "OPTIONS":
				return resp

			h = resp.headers

			h['Access-Control-Allow-Origin'] = origin
			h["Access-Control-Allow-Methods"] = get_methods()
			h["Access-Control-Max-Age"] = str(max_age)
			if headers is not None:
				h["Access-Control-Allow-Headers"] = headers
			return resp

		f.provide_automatic_options = False
		return update_wrapper(wrapped_function, f)

	return decorator

#
#
# End of cross-domain decorator
#
#

# Register blueprint
# Use "/get-game-data" for public - this is where the .htaccess file is stored (not to be confused with where the Python app is stored)
# The visualization Javascript will access datarink.com/get-game-data?gameId=###### to call the Python script
game_list_json = Blueprint('blueprint_name_for_get_game_list', __name__)
@game_list_json.route('/databot/get-game-list/')

#
#
# For cross domain
#
#

@crossdomain(origin="*")

#
#
# End for cross-domain
#
#

def getGameList():

	# Get arguments from URL
	requestDate = request.args.get("date")
	startDate = ""

	if requestDate:
		try:
			requestDate = datetime.datetime.strptime(requestDate, "%d-%m-%Y")
			startDate = requestDate - datetime.timedelta(days=7)
			startDate = startDate.strftime('%Y-%m-%d %H:%M:%S')
			requestDate = requestDate.strftime('%Y-%m-%d %H:%M:%S')
		except:
			return "Date must be formatted as dd-mm-yyyy"
	else:
		return "Specify a date"

	# Database connection
	databaseUser = dbconfig.user
	databasePasswd = dbconfig.passwd
	databaseHost = dbconfig.host
	database = dbconfig.database

	connection = pymysql.connect(user=databaseUser, passwd=databasePasswd, host=databaseHost, database=database)
	cursor = connection.cursor()

	# Variables for storing results
	games = dict()

	#
	#
	# Query for event data
	#
	#

	query = ("""
		SELECT *
		FROM events e
		WHERE (e.eventType = 'gend')
		""")
	query = query + " AND e.date <= '" + requestDate + "' AND e.date >= '" + startDate + "'"

	cursor.execute(query)
	rows = cursor.fetchall()

	# Get table column names
	columns = []
	for desc in cursor.description:
		columns.append(desc[0])

	# Turn returned rows into a dictionary so that we can use json.dumps on it later
	gameData = []
	for row in rows:
		row = dict(zip(columns, row))
		gameData.append(row)

	# Store game data
	for r in gameData:
		gameId = r["gameId"]

		games[gameId] = dict()
		games[gameId]["date"] = r["date"]
		games[gameId]["homeTeam"] = r["homeTeam"]
		games[gameId]["awayTeam"] = r["awayTeam"]
		games[gameId]["homeScore"] = r["awayScore"]
		games[gameId]["awayScore"] = r["awayScore"]
		games[gameId]["lastPeriod"] = r["period"]
		games[gameId]["lastPeriodLength"] = r["time"]

	#
	#
	# Output data
	#
	#

	results = []

	for gameId in games:

		# Convert MySQL date object to string
		dateString = games[gameId]["date"].strftime("%Y-%m-%d")

		result = {
			"gameId": gameId,
			"date": dateString,
			"homeTeam": games[gameId]["homeTeam"],
			"awayTeam": games[gameId]["awayTeam"],
			"homeScore": games[gameId]["homeScore"],
			"awayScore": games[gameId]["awayScore"],
			"lastPeriod": games[gameId]["lastPeriod"],
			"lastPeriodLength": games[gameId]["lastPeriodLength"]
		}
		results.append(result)

	return json.dumps(results)