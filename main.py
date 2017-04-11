from flask import Flask, render_template, request, redirect, url_for, request, session, abort, Response, flash
import flask_login
import src.database as db
from time import time
from random import randint
import datetime
import os
import src.challongeapi as challongeapi
#import src.smashggapi as smashggapi

app = Flask(__name__)

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Let's ride!"

# Our mock database.
user_list = db.queryMany("""SELECT username, password FROM users""")
users = {}
for user in user_list:
	users[user[0]] = {'pw': user[1]}

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	if email not in users:
		return

	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	email = request.form.get('email')
	if email not in users:
		return

	user = User()
	user.id = email
	# DO NOT ever store passwords in plaintext and always compare password
	# hashes using constant-time comparison!
	user.is_authenticated = request.form['pw'] == users[email]['pw']
	return user

@app.route('/login/', methods=['GET', 'POST'])
def login(message = None):
	if request.method == 'GET':
		return render_template("login.j2")
	if request.method == 'POST':
		email = request.form['email']
		if request.form['pw'] == users[email]['pw']:
			user = User()
			user.id = email
			flask_login.login_user(user, remember=True)
			return redirect(url_for('admin'))
		else:
			error = "Invalid Credentials. Please try again!"
			return redirect(url_for('login', message=error))

		return 'Bad login'



@app.route('/protected/')
@flask_login.login_required
def protected():
	return 'Logged in as: ' + flask_login.current_user.id


@app.route("/admin/")
@flask_login.login_required
def admin():
	return render_template("admin_home.j2")

@app.route("/admin/enter/", methods = ['POST', 'GET'])
@flask_login.login_required
def admin_enter_tournament_unsubmitted(message = None):
	return render_template("admin_enter_tournament.j2")

@app.route("/admin/entered/", methods = ['POST'])
@flask_login.login_required
def admin_enter_tournament_submitted(message = None):
	if request.method == 'POST':
		website = request.form['bracket_website']
		url = request.form['bracket_url']

		if website == "SmashGG":
			tourney_words = url.split('/')
			slug_index = tourney_words.index('tournament') + 1
			url_slug = tourney_words[slug_index]
			#smashggapi.update_rankings_for_challonge_tournament(url_slug, "melee-singles")

		elif website == "Challonge":
			tourney_words = url.split('/')
			bracket_url = tourney_words[-1]
			domain_link = tourney_words[-2]
			domain_words = domain_link.split('.')
			subdomain = None
			if domain_words[-3].lower() != "www":
				subdomain = domain_words[-3]
			#challongeapi.update_rankings_for_challonge_tournament(bracket_url, subdomain=subdomain)
			


	#return the template to enter a tournament, with a message of success or failure depending on how the code runs.

@app.route('/logout/')
def logout():
	flask_login.logout_user()
	flash('Logged out')
	return redirect(url_for('index'))

@login_manager.unauthorized_handler
def unauthorized_handler():
	flash('Unauthorized')
	return redirect(url_for('login'))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def createSetsDictionary(player_id, ForIndex = True):
	setsDictionary = {}
	if not ForIndex:
		setsDictionary["sets"] = []
	setsDictionary["id"] = player_id
	player_tuple = (player_id, player_id)

	rows = db.queryMany("""SELECT tournaments.name, tournaments.id, tournaments.calendar_date, winners.id, losers.id, winners.tag, losers.tag, winners.display_tag, losers.display_tag, sets.* FROM sets
			inner join players AS winners on sets.winner_id = winners.id
			inner join players AS losers on sets.loser_id = losers.id
			inner join tournaments on sets.db_tournament_id = tournaments.id
			WHERE (winners.id=%s or losers.id=%s)
			AND (loser_score IS NULL OR loser_score != -1)
			ORDER BY calendar_date DESC;
			""", player_tuple)
	player_set_win_count = 0
	player_set_lose_count = 0
	player_game_win_count = 0
	player_game_lose_count = 0
	tournament_count = 0
	tournament_list = []
	for row in rows:
		tournament_name = row[0]
		tournament_list.append(tournament_name)
		if row[3] == player_id:
			opponent_tag = row[8].decode('utf-8', 'ignore')
			opponent_id = row[4]
			result = "W"
			winner_score = row[12]
			loser_score = row[13]
			player_set_win_count += 1
			if winner_score and winner_score < 4 and loser_score < 3 and loser_score > -1 or loser_score == 0:
				player_game_win_count += winner_score
				player_game_lose_count += loser_score
		else:
			opponent_id = row[3]
			opponent_tag = row[7].decode('utf-8', 'ignore')
			result = "L"
			loser_score = row[12]
			winner_score = row[13]
			player_set_lose_count += 1
			if loser_score < 4 and loser_score > -1 or loser_score == 0: #people putting like 500 lol
				player_game_lose_count += loser_score
				

		calendar_date = row[2]
		tourney_id = row[1]
		score_string = str(winner_score) + '-' + str(loser_score)
		if (winner_score == None and loser_score == None): #would use Not but the way 0 is interpreted...
			score_string = "NR"
		set_tuple = (tournament_name, opponent_tag, result, calendar_date, score_string, tourney_id, opponent_id)

		if not ForIndex:
			setsDictionary["sets"].append(set_tuple)
	tourney_attended_count = len(list(set(tournament_list)))


	row = db.queryOne("""SELECT trueskill_mu, trueskill_sigma, Round((trueskill_mu-3*trueskill_sigma),3), display_tag, main_character, main_color, alternate_character, alternate_color as weighted_trueskill
				FROM players
				WHERE id=%s""", (player_id,))
	mu = float(row[0])
	sigma = float(row[1])
	weighted_trueskill = row[2]
	setsDictionary["mu"] = round (mu * 100, 3)
	setsDictionary["sigma"] = round(sigma * 100, 3)
	setsDictionary["weighted_trueskill"] = weighted_trueskill
	setsDictionary["trueskill_thousand_test"] = int(round(100 * weighted_trueskill,0))
	setsDictionary["display_name"] = row[3].decode('utf-8', 'ignore')
	setsDictionary["set_win_count"] = player_set_win_count
	setsDictionary["set_lose_count"] = player_set_lose_count
	setsDictionary["total_set_count"] = player_set_win_count + player_set_lose_count
	setsDictionary["game_win_count"] = player_game_win_count
	setsDictionary["game_lose_count"] = player_game_lose_count
	setsDictionary["total_game_count"] = player_game_win_count + player_game_lose_count
	
	setsDictionary["main_character"] = "sandbag"
	setsDictionary["main_color"] = None
	setsDictionary["alternate_character"] = None
	setsDictionary["alternate_color"] = None
	if row[4]:
		setsDictionary["main_character"] = row[4]
		if row[5]:
			setsDictionary["main_color"] = row[5]
		if row[6]:
			setsDictionary["alternate_character"] = row[6]
		if row[7]:
			setsDictionary["alternate_color"] = row[7]

	try:
		setsDictionary["set_win_percent"] = round(100 * float(player_set_win_count)/float(player_set_win_count + player_set_lose_count), 1)
		setsDictionary["game_win_percent"] = round(100 * float(player_game_win_count)/float(player_game_win_count + player_game_lose_count), 1)
	except ZeroDivisionError: 
		setsDictionary["set_win_percent"] = 0.0
		setsDictionary["game_win_percent"] = 0.0
	setsDictionary["tourney_attended_count"] = tourney_attended_count

	return setsDictionary

def roundToMultBelow(num, multiple):
	return num - (num % multiple)

def gradientVal(maxCol, minCol, maxVal, minVal, val):
	return int(round((maxCol - minCol) * (float(val - minVal) / (maxVal - minVal)) + minCol))

def getSkillDistribution(rows, player_id = -1):
	minTrueSkill = int(round(100 * min(rows, key=lambda	row: row[1])[1]))
	maxTrueSkill = int(round(100 * max(rows, key=lambda	row: row[1])[1]))
	startRange = roundToMultBelow(minTrueSkill, 50) - 250
	endRange = roundToMultBelow(maxTrueSkill, 50) + 250
	counts = [0] * (((endRange - startRange) / 50) + 1)

	playerCountIndex = -1

	for row in rows:
		index = ((roundToMultBelow(int(round(100 * row[1])), 50) - startRange) / 50)
		if (row[0] == player_id):
			playerCountIndex = index
		counts[index] += 1


	maxCount = max(counts)
	half = sorted(filter(lambda count: count > 0, counts))[len(counts)/2]

	skillDistribution = []
	for i in range(len(counts)):
		startPos = startRange + (50 * i)
		#print("{} - {}".format(startPos, startPos + 49))

		if (counts[i] > half):
			g = gradientVal(180, 72, maxCount, half, counts[i])
			r = gradientVal(36, 0, maxCount, half, counts[i])
		else:
			r = gradientVal(72, 255, half, 0, counts[i])
			g = gradientVal(36, 0, half, 0, counts[i])

		skillDistribution.append({
			"numPeople": counts[i],
			"range": "{} $ {}".format(startPos, startPos + 49),
			"backgroundColor": "rgba({},{},0,0.666)".format(r,g),
			"borderColor": "rgba({},{},0,1)".format(r,g)
			})

	if playerCountIndex > -1:
		for i in range(len(skillDistribution)):
			if i != playerCountIndex:
				skillDistribution[i]["backgroundColor"] = skillDistribution[i]["backgroundColor"].replace("0.666", "0.25")
				skillDistribution[i]["borderColor"] = skillDistribution[i]["borderColor"].replace("1)", "0.45)")

	return skillDistribution


activityRequirementDate = str((datetime.datetime.now() - datetime.timedelta(days=60)).date())

def newIndexDictionary(Page=None):
	allPlayers = {}
	allPlayers["players"] = []
	graphRows = db.queryMany("""SELECT ALL_T.pid, ALL_T.weighted_trueskill, ALL_T.main_character, ALL_T.main_color, COUNT(DISTINCT(ALL_T.tid)) FROM
							(
						        SELECT players.id AS pid, tournaments.id AS tid, tournaments.calendar_date, location, tag, main_character, main_color,
						              Round((trueskill_mu-3*trueskill_sigma),3) AS weighted_trueskill FROM players
						        LEFT join sets as losing_sets on players.id = losing_sets.winner_id
						        inner join tournaments on losing_sets.db_tournament_id = tournaments.id
						    UNION
						        SELECT players.id AS pid, tournaments.id AS tid, tournaments.calendar_date, location, tag, main_character, main_color,
						              Round((trueskill_mu-3*trueskill_sigma),3) AS weighted_trueskill FROM players
						        LEFT join sets as winning_sets on players.id = winning_sets.winner_id
						        inner join tournaments on winning_sets.db_tournament_id = tournaments.id) AS ALL_T
							where ALL_T.calendar_date > %s AND ALL_T.location = 'WA'
							group by ALL_T.pid, ALL_T.weighted_trueskill, ALL_T.main_character, ALL_T.main_color
							order by ALL_T.weighted_trueskill desc
							""", (activityRequirementDate,))

	allPlayers["skillDistribution"] = getSkillDistribution(graphRows)
	allPlayers["player_count"] = float(len(graphRows))

	pageOffset = 0
	if Page:
		pageNumber = Page - 1
		pageOffset = pageNumber * 50
		pageSliceOffset = (pageNumber + 1) * 50
		print "pageOffset", pageOffset

	for row in graphRows[pageOffset:pageSliceOffset]:
		pageOffset += 1
		player_id = str(row[0])
		playerinfo = createSetsDictionary(row[0])
		playerinfo["rank"] = pageOffset 
		playerinfo["character"] = "sandbag"
		if row[2]:
			playerinfo["character"] = row[2]
		playerinfo["color"] = None
		if row[3]:
			playerinfo["color"] = row[3]	
		allPlayers["players"].append(playerinfo)

	return allPlayers

@app.route("/")
def rerouteSlash():
	return redirect(url_for("index"))

@app.route('/rankings/1')
@app.route('/rankings/<int:page>')
def index(page=1):
	indexDictionary = newIndexDictionary(Page=page)
	final_page_number = int((indexDictionary["player_count"] / 50) + 1)
	indexDictionary["last_update"] = db.queryOne("""SELECT calendar_date FROM tournaments ORDER BY calendar_date DESC LIMIT 1;""")[0]
	indexDictionary["last_page_2"] = page - 2
	indexDictionary["last_page"] = page - 1
	indexDictionary["current_page"] = page
	indexDictionary["next_page"] = page + 1
	indexDictionary["next_page_2"] = page + 2
	indexDictionary["final_page_number"] = final_page_number


	return render_template("index.j2", **indexDictionary).encode("utf-8")

@app.route("/player/<int:player_id>")
def player(player_id):
	rows = db.queryMany("""SELECT ALL_T.pid, ALL_T.weighted_trueskill, ALL_T.main_character, ALL_T.main_color, COUNT(DISTINCT(ALL_T.tid)) FROM
							(
						        SELECT players.id AS pid, tournaments.id AS tid, tournaments.calendar_date, location, tag, main_character, main_color,
						              Round((trueskill_mu-3*trueskill_sigma),3) AS weighted_trueskill FROM players
						        LEFT join sets as losing_sets on players.id = losing_sets.winner_id
						        inner join tournaments on losing_sets.db_tournament_id = tournaments.id
						    UNION
						        SELECT players.id AS pid, tournaments.id AS tid, tournaments.calendar_date, location, tag, main_character, main_color,
						              Round((trueskill_mu-3*trueskill_sigma),3) AS weighted_trueskill FROM players
						        LEFT join sets as winning_sets on players.id = winning_sets.winner_id
						        inner join tournaments on winning_sets.db_tournament_id = tournaments.id) AS ALL_T
							where ALL_T.calendar_date > %s AND ALL_T.location = 'WA'
							group by ALL_T.pid, ALL_T.weighted_trueskill, ALL_T.main_character, ALL_T.main_color
							order by ALL_T.weighted_trueskill desc
							""", (activityRequirementDate,))
	setsDictionary = createSetsDictionary(player_id, ForIndex=False)
	setsDictionary["skillDistribution"] = getSkillDistribution(rows, player_id)
	return render_template("player.j2", **setsDictionary).encode("utf-8")


@app.route("/tournaments/")
def tournaments():
	tournamentDictionary = {}
	tournamentDictionary["tournaments"] = []

	rows = db.queryMany("""SELECT name, website, url, calendar_date, id, subdomain
				FROM tournaments
				ORDER BY calendar_date DESC;
				""")

	for row in rows:
		name = row[0]
		if row[5]:
			subdomain = row[5] + "."
		else:
			subdomain = ""	
		if row[1] == "challonge":
			website = str("https://" + subdomain + row[1] + ".com/" + row[2])
		else:
			website = str("https://smash.gg/" + row[2])
		calendar_date = row[3]
		tourney_id = row[4]
		tournament_tuple = (name, website, calendar_date, tourney_id)
		tournamentDictionary["tournaments"].append(tournament_tuple)

	return render_template("tournaments.j2", **tournamentDictionary).encode("utf-8")


@app.route("/tournaments/<int:tournament_id>")
def tournamentPage(tournament_id):
	tournamentWebPageDictionary = {}
	tournamentWebPageDictionary["players"] = []
	tournamentWebPageDictionary["sets"] = []
	tournamentWebPageDictionary["information"] = {}

	row = db.queryOne("""SELECT * FROM tournaments
				WHERE id=%s;
				""", (tournament_id,))
	if row[6]:
		subdomain = row[6] + "."
	else:
		subdomain = ""
	tourney_id = row[0]
	name = row[1]
	if row[5] == "challonge":
		url = "https://" + subdomain + row[5] + ".com/" + row[2]
	else:
		url = "https://smash.gg/" + row[2]
	calendar_date = row[3]
	tournamentWebPageDictionary["information"]["tournament_id"] = tournament_id
	tournamentWebPageDictionary["information"]["name"] = name
	tournamentWebPageDictionary["information"]["url"] = url
	tournamentWebPageDictionary["information"]["calendar_date"] = calendar_date

	rows = db.queryMany("""SELECT winners.display_tag, losers.display_tag, winners.id, losers.id, sets.* FROM sets 
				INNER JOIN players as winners on sets.winner_id = winners.id
				INNER JOIN players as losers on sets.loser_id = losers.id
				AND loser_score != -1
				WHERE db_tournament_id=%s""", (tournament_id,))
	player_list = []
	for row in rows:
		winner_tag = row[0].decode('utf-8', 'ignore')
		loser_tag = row[1].decode('utf-8', 'ignore')
		winner_id = row[2]
		loser_id = row[3]
		winner = (winner_tag, winner_id)
		loser = (loser_tag, loser_id)
		winner_score = row[7]
		loser_score = row[8]
		score_string = str(winner_score) + '-' + str(loser_score)
		if (winner_score == None and loser_score == None):
			score_string = "Not Reported"
		elif winner_score == -1 or loser_score == -1:
			score_string = "DQ"
		set_tuple = (winner, loser, score_string)
		tournamentWebPageDictionary["sets"].append(set_tuple)
		if winner not in player_list or loser not in player_list:
			player_list.append(winner)
			player_list.append(loser)

	tournamentWebPageDictionary["players"] = (list(set(player_list)))
	tournamentWebPageDictionary["players"].sort(key = lambda s: s[0].lower())

	return render_template("tournamentpage.j2", **tournamentWebPageDictionary).encode("utf-8")

@app.route("/about")
def about():
	return render_template("about.j2")

#do we need to pass every player as some part of a dictionary to have their names pop up
#when typing them in a search?
@app.route("/search/")
def search():
	player = request.args.get('Player').lower().strip()
	playerquery = db.queryOne("""SELECT id FROM players WHERE tag=%s""",((player,)))
	if playerquery:
		player_id = playerquery[0]
		return redirect(url_for('player', player_id = player_id))
	else:
		return redirect(request.headers.get("Referer"))


@app.route("/head2head/search/", methods = ['GET'])
def searchh2h(message=None):
	playersDictionary = {}
	playersDictionary["players"] = []
	randomInt = randint(0,1)
	playersDictionary["randomInt"] = randomInt

	rows = db.queryMany("""SELECT display_tag FROM players""")
	for row in rows:
		playersDictionary["players"].append(row[0].decode('utf-8', 'ignore'))
		playersDictionary["players"].sort(key = lambda s: s[0].lower())
	return render_template("searchh2h.j2", **playersDictionary).encode("utf-8")

@app.route('/head2head/', methods = ['GET'])
def returnh2h():
	if request.method == 'GET':

		p1 = request.args.get('Player1').lower().strip()
		p2 = request.args.get('Player2').lower().strip()
		p1query = db.queryOne("""SELECT id FROM players WHERE tag=%s""",((p1,)))
		p2query = db.queryOne("""SELECT id FROM players WHERE tag=%s""",((p2,)))
		if p1query and p2query:
			player_1_id = p1query[0]
			player_2_id = p2query[0]
			head2headDictionary = {}
			head2headDictionary["sets"] = []
			head2headDictionary["player_1_id"] = player_1_id
			head2headDictionary["player_2_id"] = player_2_id
			head2headDictionary["player_1_set_wins"] = 0
			head2headDictionary["player_2_set_wins"] = 0
			head2headDictionary["player_1_game_wins"] = 0
			head2headDictionary["player_2_game_wins"] = 0
			players_tuple = (player_1_id, player_2_id, player_2_id, player_1_id,)

			row = db.queryOne("""SELECT display_tag FROM players WHERE id=%s""", (player_1_id,))
			head2headDictionary["player_1_tag"] = row[0]
			row = db.queryOne("""SELECT display_tag FROM players WHERE id=%s""", (player_2_id,))
			head2headDictionary["player_2_tag"] = row[0]

			rows = db.queryMany("""SELECT tournaments.name, tournaments.id, tournaments.calendar_date, winners.id, losers.id, winners.tag, losers.tag, winners.display_tag, losers.display_tag, sets.* FROM sets
					inner join players AS winners on sets.winner_id = winners.id
					inner join players AS losers on sets.loser_id = losers.id
					inner join tournaments on sets.db_tournament_id = tournaments.id
					WHERE (winners.id=%s and losers.id=%s)
					OR (winners.id=%s and losers.id=%s)
					AND (loser_score IS NULL OR loser_score != -1)
					ORDER BY calendar_date DESC;
					""", players_tuple)
			count = 0
			for row in rows:
				count += 1

				tournament_name = row[0]
				tournament_id = row[1]
				tournament_date = row[2]
				winner_id = row[3]
				loser_id = row[4]
				winner_display_tag = row[7].decode('utf-8', 'ignore')
				loser_display_tag = row[8].decode('utf-8', 'ignore')
				if (row[12] == None or row[13] == None):
					score_string = "Not Reported"
				else:
					score_string = str(row[12]) + '-' + str(row[13])
				set_tuple = (tournament_name, tournament_id, tournament_date, winner_id, loser_id, winner_display_tag, loser_display_tag, score_string)
				head2headDictionary["sets"].append(set_tuple)
				if winner_id == player_1_id:
					head2headDictionary["player_1_set_wins"] += 1
					if type(row[12]) == int and type(row[13]) == int:
						head2headDictionary["player_1_game_wins"] += row[12]
						head2headDictionary["player_2_game_wins"] += row[13]
				else:
					head2headDictionary["player_2_set_wins"] += 1
					if type(row[12]) == int and type(row[13]) == int:
						head2headDictionary["player_2_game_wins"] += row[12]
						head2headDictionary["player_1_game_wins"] += row[13]
			return render_template("head2head.j2", **head2headDictionary).encode("utf-8")
		else:
			message = "Player(s) could not be found. Please try again!"
			return render_template('searchh2h.j2', message = message)

@app.route('/submit/', methods = ['POST', 'GET'])
def submit_form_unsubmitted(messsage=None):
	return render_template("submit_form.j2")

@app.route('/submitted/', methods = ['POST', 'GET'])
def submit_form_submitted():
	if request.method == 'POST':
		try:
			name = request.form['Name']
			tag = request.form['Tag']
			contact = request.form['Contact']
			date = datetime.datetime.now().isoformat()
			info = request.form['Information']
			issue_type = request.form['Issue']

			submit_tuple = (name, tag, contact, issue_type, info, date)

			db.queryInsert("""INSERT INTO submitted_forms(name, tag, contact, issue_type, information, date_time) 
							VALUES(%s,%s,%s,%s,%s,%s)""",
							submit_tuple)

			message = "Your concern was successfully submitted! We hear you loud and clear and we'll look in to fixing this issue."
		except: 
			message = "Your concern is important to us but could not be submitted at this time. Please try again!"
		finally:
			return render_template("submit_form.j2", message=message)

#put this behind some kind of login credentials
@app.route('/submit/list')
@flask_login.login_required
def submit_form_view():
	submittedChangesDictionary = {}
	submittedChangesDictionary["changes"] = []
	rows = db.queryMany("""SELECT * FROM submitted_forms""")

	for row in rows:
		id_number = row[0]
		name = row[1]
		tag = row[2]
		contact = row[3]
		issue_type = row[4]
		info = row[5]
		date = row[6]
		change_tuple = (id_number, name, tag, contact, issue_type, info, date)
		submittedChangesDictionary["changes"].append(change_tuple)

	return render_template("submittedforms.j2", **submittedChangesDictionary).encode("utf-8") 

@app.context_processor
def inject_time():
	return dict(timestamp=int(time()))


if __name__ == "__main__":
	app.secret_key = os.urandom(12)
	app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))








