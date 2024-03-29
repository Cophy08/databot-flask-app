from flask import Blueprint
from flask import request
from pprint import pprint
from collections import namedtuple
from itertools import combinations
from datetime import datetime
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
game_json = Blueprint('blueprint_name_for_get_game_data', __name__)
@game_json.route('/databot/get-game-data/')

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

def getGameData():

	# Get arguments from URL
	gameId = request.args.get("gameId")
	season = request.args.get("season")
	team = request.args.get("team")
	requestDate = request.args.get("date")

	# Database connection
	databaseUser = dbconfig.user
	databasePasswd = dbconfig.passwd
	databaseHost = dbconfig.host
	database = dbconfig.database

	connection = pymysql.connect(user=databaseUser, passwd=databasePasswd, host=databaseHost, database=database)
	cursor = connection.cursor()

	# Variables for storing results
	playerProperties = dict()
	playerShifts = dict()
	events = dict()
	periodDurations = dict()
	teammatePairingTois = dict()
	opponentPairingTois = dict()
	ppTimes = dict()

	#
	#
	# Query for event data
	#
	#

	query = ("""
		SELECT *
		FROM events e
		WHERE (e.eventType = 'pend' OR e.eventType = 'goal' OR e.eventType = 'shot' OR e.eventType = 'miss' OR e.eventType = 'block')
		""")

	# Check if enough parameters have been specified
	# gameId + season gets priority over team + date
	if (not requestDate or not team) and (not gameId or not season):
		return "Must specify a date + team combination, or a gameId + season combination"
	elif gameId and season:
		query = query + " AND e.season = " + season + " AND e.gameId = " + gameId
	elif team and requestDate:
		# Convert date string to date object if string is not empty
		try:
			requestDate = datetime.datetime.strptime(requestDate, "%d-%m-%Y")
			requestDate = requestDate.strftime('%Y-%m-%d %H:%M:%S')
		except:
			return "Date must be formatted as dd-mm-yyyy"
		query = query + " AND e.date = '" + requestDate + "' AND (e.awayTeam = '" + team + "' OR e.homeTeam = '" + team + "')"

		# Clear gameId - we'll replace it with the gameId returned by the query result to ensure it's consistent with the team + date arguments
		# Because of how the players table is structured, we'll always query the shift and player data using gameId
		gameId = None
		season = None

	cursor.execute(query)
	rows = cursor.fetchall()

	# Get table column names
	columns = []
	for desc in cursor.description:
		columns.append(desc[0])

	# Turn returned rows into a dictionary so that we can use json.dumps on it later
	eventData = []
	for row in rows:
		row = dict(zip(columns, row))
		eventData.append(row)

	# Initialize dictionaries
	for r in eventData:
		if r["eventType"] <> "pend":
			eventKey = r["playId"]
			events[eventKey] = dict()
			events[eventKey]["eventTeam"] = r["eventTeam"]
			events[eventKey]["eventType"] = r["eventType"]
			events[eventKey]["eventP1"] = r["eventP1"]
			events[eventKey]["period"] = r["period"]
			events[eventKey]["time"] = r["time"]
			events[eventKey]["homeSkaters"] = [r["homeS1"], r["homeS2"], r["homeS3"], r["homeS4"], r["homeS5"], r["homeS6"]]
			events[eventKey]["awaySkaters"] = [r["awayS1"], r["awayS2"], r["awayS3"], r["awayS4"], r["awayS5"], r["awayS6"]]
			events[eventKey]["homeGoalie"] = r["homeG"]
			events[eventKey]["awayGoalie"] = r["awayG"]
		elif r["eventType"] == "pend":
			periodDurations[r["period"]] = r["time"]

		# If querying by team + date, then store the gameId because we'll always query the shift and player data using the gameId
		if team and requestDate and not gameId:
			gameId = str(r["gameId"])
		if team and requestDate and not season:
			season = str(r["season"])

	# Store the duration of each period and store the team names
	pendEvents = [e for e in eventData if e["eventType"] == "pend"]
	teams = []
	for r in pendEvents:
		periodDurations[r["period"]] = r["time"]
		if len(teams) < 2:
			teams = []
			teams.append(r["awayTeam"])
			teams.append(r["homeTeam"])

	#
	#
	# Query for shift data and player properties
	#
	#

	query = ("""
		SELECT s.season, s.date, s.gameId, s.opponent, s.playerId, s.period, s.start, s.end, p.team AS team, p.number AS number, p.name AS name, p.position AS position
		FROM shifts s
		LEFT JOIN players AS p
			ON (p.playerId = s.playerId AND p.gameId = s.gameId and p.season = s.season)
		""")

	query = query + " WHERE s.season = " + season + " AND s.gameId = " + gameId

	cursor.execute(query)
	rows = cursor.fetchall()

	# Get table column names
	columns = []
	for desc in cursor.description:
		columns.append(desc[0])

	# Turn returned rows into a dictionary so that we can use json.dumps on it later
	shiftData = []
	for row in rows:
		row = dict(zip(columns, row))
		shiftData.append(row)

	# Initialize dictionaries
	playerProperties[teams[1]] = dict()
	playerProperties[teams[0]] = dict()

	playerShifts[teams[1]] = dict()
	playerShifts[teams[0]] = dict()

	teammatePairingTois[teams[1]] = dict()
	teammatePairingTois[teams[0]] = dict()

	ppTimes[teams[1]] = dict()
	ppTimes[teams[0]] = dict()
	for per in periodDurations:
		ppTimes[teams[1]][per] = set()
		ppTimes[teams[0]][per] = set()

	for r in shiftData:
		playerKey = r["playerId"]

		if playerKey not in playerShifts:
			playerShifts[r["team"]][playerKey] = dict()

		if playerKey not in playerProperties:
			playerProperties[r["team"]][playerKey] = dict()
			playerProperties[r["team"]][playerKey]["name"] = r["name"]
			playerProperties[r["team"]][playerKey]["number"] = r["number"]
			playerProperties[r["team"]][playerKey]["position"] = r["position"]
			playerProperties[r["team"]][playerKey]["toi"] = 0
			playerProperties[r["team"]][playerKey]["ev5Toi"] = 0

	# Populate the playerShifts dictionary for each player
	for r in shiftData:
		playerKey = r["playerId"]
		shiftKey = str(r["period"]) + "&" + str(r["start"])
		playerShifts[r["team"]][playerKey][shiftKey] = dict()
		playerShifts[r["team"]][playerKey][shiftKey]["period"] = r["period"]
		playerShifts[r["team"]][playerKey][shiftKey]["start"] = r["start"]
		playerShifts[r["team"]][playerKey][shiftKey]["end"] = r["end"]

	cursor.close()
	connection.close()

	#
	#
	# Get ev5 matchups
	# Also record power plays
	#
	#

	for per in periodDurations:

		#
		#
		# Create a dictionary of each player's shifts for each team
		# For each player, create a set for all seconds that the player was on the ice
		# The set's entries are 0-based: a player who played the first 5 seconds of the period would have [0, 1, 2, 3, 4] in his set
		#
		#

		# Get all shifts in this period
		# Also get a list of unique playerIds who had a shift in this period
		periodShifts = dict()
		periodPlayers = dict()
		periodSkaters = dict()
		periodGoalies = dict()

		for team in teams:
			periodShifts[team] = [s for s in shiftData if s["period"] == per and s["team"] == team]
			shiftsWithUniquePlayers = { s["playerId"]:s for s in periodShifts[team] }.values()
			periodPlayers[team] = [s["playerId"] for s in shiftsWithUniquePlayers]
			periodSkaters[team] = [s["playerId"] for s in shiftsWithUniquePlayers if s["position"] != "g"]
			periodGoalies[team] = [s["playerId"] for s in shiftsWithUniquePlayers if s["position"] == "g"]

		# Create sets for each player's shifts
		playerShiftsInPeriod = dict()
		for team in teams:
			playerShiftsInPeriod[team] = dict()

			for p in periodPlayers[team]:
				playerShiftsInPeriod[team][p] = set()

			for s in periodShifts[team]:
				playerShiftsInPeriod[team][s["playerId"]].update(range(s["start"], s["end"]))

		#
		#
		# Record how many players, skaters, and goalies were on the ice for each team at each second
		#
		#

		combinedSkaterList = dict()
		combinedGoalieList = dict()
		skaterCounts = dict()
		goalieCounts = dict()

		for team in teams:

			# Create a list that stores all set values from each player shift set
			# The list will contain repeated values (e.g., if 5 skaters were on-ice at t=1, then we'll have five 1's in the list)
			# Do the same for goalies
			combinedSkaterList[team] = []
			for p in periodSkaters[team]:
				combinedSkaterList[team].extend(playerShiftsInPeriod[team][p])

			combinedGoalieList[team] = []
			for p in periodGoalies[team]:
				combinedGoalieList[team].extend(playerShiftsInPeriod[team][p])

			# Initialize list where the value at each index (seconds elapsed) represents the number of skaters on ice
			skaterCounts[team] = [-1] * periodDurations[per]
			goalieCounts[team] = [-1] * periodDurations[per]

			# Count the number of skaters and goalies on at each second
			for t in range(0, periodDurations[per]):
				skaterCounts[team][t] = combinedSkaterList[team].count(t)
				goalieCounts[team][t] = combinedGoalieList[team].count(t)

		#
		#
		# Record ev5 times and powerplay times
		#
		#

		ev5Times = set()

		for t in range(0, periodDurations[per]):

			# Record the ev5 times
			if skaterCounts[teams[0]][t] == 5 and skaterCounts[teams[1]][t] == 5 and goalieCounts[teams[0]][t] == 1 and goalieCounts[teams[1]][t] == 1:
				ev5Times.add(t)

			# Record the powerplay times for each team
			playerCountDiff = (skaterCounts[teams[1]][t] + goalieCounts[teams[1]][t]) - (skaterCounts[teams[0]][t] + goalieCounts[teams[0]][t])
			if playerCountDiff < 0:
				ppTimes[teams[0]][per].add(t)
			elif playerCountDiff > 0:
				ppTimes[teams[1]][per].add(t)

		#
		#
		# Record individual player's TOI
		#
		#

		for team in teams:
			for player in playerShiftsInPeriod[team]:
				playerProperties[team][player]["toi"] += len(playerShiftsInPeriod[team][player])
				playerProperties[team][player]["ev5Toi"] += len(set.intersection(ev5Times, playerShiftsInPeriod[team][player]))

		#
		#
		# For each combination of skaters (teammates and opponents), get the total ev5 time together by getting the intersect of their shifts AND ev5 times
		#
		#

		# Teammate pairings
		for team in teams:
			pairings = list(combinations(playerShiftsInPeriod[team], 2))

			for pairing in pairings:

				# Create the pairing key - the lower playerId is always first in the key
				if pairing[0] < pairing[1]:
					pairingKey = str(pairing[0]) + "&" + str(pairing[1])
				elif pairing[1] < pairing[0]:
					pairingKey = str(pairing[1]) + "&" + str(pairing[0])

				# Create dictionary entry if the pairing doesn't already exist
				if pairingKey not in teammatePairingTois[team]:
					teammatePairingTois[team][pairingKey] = 0

				# Increment ev5 TOI of pairing
				teammatePairingTois[team][pairingKey] += len(set.intersection(ev5Times, playerShiftsInPeriod[team][pairing[0]], playerShiftsInPeriod[team][pairing[1]]))

		# Opponent pairings
		for p1 in playerShiftsInPeriod[teams[0]]:

			if playerProperties[teams[0]][p1]["position"] == "g":
					continue

			for p2 in playerShiftsInPeriod[teams[1]]:

				if playerProperties[teams[1]][p2]["position"] == "g":
					continue

				# The opponent pairing's pairingKey is always <away player> & <home player>
				pairingKey = str(p1) + "&" + str(p2)

				# Create dictionary entry if the pairing doesn't already exist
				if pairingKey not in opponentPairingTois:
					opponentPairingTois[pairingKey] = 0

				# Increment ev5 TOI of pairing
				opponentPairingTois[pairingKey] += len(set.intersection(ev5Times, playerShiftsInPeriod[teams[0]][p1], playerShiftsInPeriod[teams[1]][p2]))

	#
	#
	# Convert powerplay sets into ranges for json output
	#
	#

	ppRanges = dict()
	ppRanges[teams[1]] = dict()
	ppRanges[teams[0]] = dict()
	for per in periodDurations:
		ppRanges[teams[1]][per] = dict()
		ppRanges[teams[0]][per] = dict()

	for team in ppTimes:
		for per in ppTimes[team]:
			ppTimesList = list(ppTimes[team][per])
			ppTimesList.sort()
			ppStart = -1
			ppEnd = -1
			for i, sec in enumerate(ppTimesList):
				if i == 0:
					ppStart = sec
				else:
					if sec - ppTimesList[i - 1] > 1:
						# Create a range if the current time does not immediately follow the previous time (i.e., the difference is more than 1 second)
						ppEnd = ppTimesList[i - 1]
						ppRanges[team][per][ppStart] = ppEnd
						ppStart = sec
						ppEnd = -1
					elif i == len(ppTimesList) - 1:
						# Create a range if the current time is the final value in the list of this period's powerplay times
						ppEnd = sec
						ppRanges[team][per][ppStart] = ppEnd
						ppStart = -1
						ppEnd = -1

	#
	#
	# Return results
	#
	#

	results = []

	# Return period durations
	for per in periodDurations.keys():
		result = {
			"type": "period",
			"period": per,
			"duration": periodDurations[per]
		}
		results.append(result)

	# Return player properties
	for team in playerProperties:
		for player in playerProperties[team]:
			result = {
				"type": "player",
				"playerId": player,
				"team": team,
				"name": playerProperties[team][player]["name"],
				"number": playerProperties[team][player]["number"],
				"position": playerProperties[team][player]["position"],
				"toi": playerProperties[team][player]["toi"],
				"ev5Toi": playerProperties[team][player]["ev5Toi"]
			}
			results.append(result)

	# Return shift data
	for team in playerProperties:
		for player in playerShifts[team]:
			for shift in playerShifts[team][player]:
				result = {
					"type": "shift",
					"playerId": player,
					"team": team,
					"period": playerShifts[team][player][shift]["period"],
					"start": playerShifts[team][player][shift]["start"],
					"end": playerShifts[team][player][shift]["end"]
				}
				results.append(result)

	# Return ev5 pairing TOIs
	for team in teammatePairingTois:
		for pairing in teammatePairingTois[team]:
			result = {
				"type": "teammates",
				"team": team,
				"playerIds": pairing,
				"toi": teammatePairingTois[team][pairing]
			}
			results.append(result)

	for pairing in opponentPairingTois:
		result = {
			"type": "opponents",
			"playerIds": pairing,
			"toi": opponentPairingTois[pairing]
		}
		results.append(result)

	# Return powerplay ranges
	for team in ppRanges:
		for period in ppRanges[team]:
			for start in ppRanges[team][period]:
				result = {
					"type": "powerplay",
					"team": team,
					"period": period,
					"start": start,
					"end": ppRanges[team][period][start]
				}
				results.append(result)

	# Return event data
	for event in events:
		result = {
			"type": "event",
			"id": event,
			"eventTeam": events[event]["eventTeam"],
			"eventType": events[event]["eventType"],
			"eventP1": events[event]["eventP1"],
			"period": events[event]["period"],
			"time": events[event]["time"],
			"homeSkaters": events[event]["homeSkaters"],
			"awaySkaters": events[event]["awaySkaters"],
			"homeGoalie": events[event]["homeGoalie"],
			"awayGoalie": events[event]["awayGoalie"]
		}
		results.append(result)

	result = {
		"type": "teams",
		"home": teams[1],
		"away": teams[0]
	}
	results.append(result)

	return json.dumps(results)