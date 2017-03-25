from flask import Flask, render_template, request, redirect, url_for, request, session, abort

import src.database as db
from time import time
import datetime

app = Flask(__name__)

@app.route("/")
def index():
	playerRankingDictionary = {}
	playerRankingDictionary["players"] = []


	rows = db.queryMany("""SELECT tag, display_tag, Round((trueskill_mu-3*trueskill_sigma),3) AS weighted_trueskill, id 
					FROM players 
					WHERE players.location = 'WA' 
					ORDER BY weighted_trueskill desc;
					""")
	count = 0
	for row in rows:
		count += 1
		display_tag, weighted_trueskill, player_id = row[1], row[2], row[3]
		player_tuple = (count, display_tag, weighted_trueskill, player_id)

		playerRankingDictionary["players"].append(player_tuple)


	playerRankingDictionary["last_update"] = db.queryOne("""SELECT calendar_date FROM tournaments ORDER BY calendar_date DESC LIMIT 1;""")[0]

	return render_template("index.j2", **playerRankingDictionary).encode("utf-8")

@app.route("/login/", methods=['POST', 'GET'])
def login():
	error = None
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		completion = validate(username, password)
		if completion == False:
			error = 'Invalid Credentials. Please try again.'
		else:
			return redirect(url_for('secret'))
	return render_template('login.j2', error=error)

def validate(username, password):
	completion = False
	rows = db.queryMany("SELECT * FROM users")
	for row in rows:
		dbUser = row[1]
		dbPass = row[2]
		if dbUser==username and dbPass==password:
			completion=True
	return completion

@app.route('/secret')
def secret():
	return "This is a secret page!"


@app.route("/player/<int:player_id>")
def player(player_id):
	setsDictionary = {}
	setsDictionary["sets"] = []
	setsDictionary["id"] = player_id
	player_tuple = (player_id, player_id)

	rows = db.queryMany("""SELECT tournaments.name, tournaments.id, tournaments.calendar_date, winners.id, losers.id, winners.tag, losers.tag, winners.display_tag, losers.display_tag, sets.* FROM sets
			inner join players AS winners on sets.winner_id = winners.id
			inner join players AS losers on sets.loser_id = losers.id
			inner join tournaments on sets.db_tournament_id = tournaments.id
			WHERE (winners.id=? or losers.id=?)
			AND (loser_score IS NULL OR loser_score != -1)
			ORDER BY calendar_date DESC;
			""", player_tuple)

	for row in rows:
		tournament_name = row[0]
		if row[3] == player_id:
			opponent_tag = row[8]
			opponent_id = row[4]
			result = "W"
			winner_score = row[12]
			loser_score = row[13]
		else:
			opponent_id = row[3]
			opponent_tag = row[7]
			result = "L"
			loser_score = row[12]
			winner_score = row[13]
		calendar_date = row[2]
		tourney_id = row[1]
		score_string = str(winner_score) + '-' + str(loser_score)
		set_tuple = (tournament_name, opponent_tag, result, calendar_date, score_string, tourney_id, opponent_id)
		setsDictionary["sets"].append(set_tuple)

	row = db.queryOne("""SELECT trueskill_mu, trueskill_sigma, (trueskill_mu-3*trueskill_sigma), display_tag as weighted_trueskill
				FROM players
				WHERE id=?""", (player_id,))
	mu = row[0]
	sigma = row[1]
	weighted_trueskill = row[2]
	setsDictionary["mu"] = round(mu, 3)
	setsDictionary["sigma"] = round(sigma, 3)
	setsDictionary["weighted_trueskill"] = round(weighted_trueskill, 3)
	setsDictionary["display_name"] = row[3]

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
				WHERE id=?;
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
				WHERE db_tournament_id=?""", (tournament_id,))
	player_list = []
	for row in rows:
		winner_tag = row[0]
		loser_tag = row[1]
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
	player = request.args.get('Player').lower()
	playerquery = db.queryOne("""SELECT id FROM players WHERE tag=?""",((player,)))
	if playerquery:
		player_id = playerquery[0]
		return redirect(url_for('player', player_id = player_id))
	else:
		print "fuck"
		return redirect(url_for('index'))


@app.route("/head2head/search/", methods = ['GET'])
def searchh2h(message=None):
	playersDictionary = {}
	playersDictionary["players"] = []
	rows = db.queryMany("""SELECT display_tag FROM players""")
	for row in rows:
		playersDictionary["players"].append(row[0])
		playersDictionary["players"].sort(key = lambda s: s[0].lower())
	return render_template("searchh2h.j2", **playersDictionary).encode("utf-8")

@app.route('/head2head/', methods = ['GET'])
def returnh2h():
	if request.method == 'GET':

		p1 = request.args.get('Player1').lower()
		p2 = request.args.get('Player2').lower() 
		p1query = db.queryOne("""SELECT id FROM players WHERE tag=?""",((p1,)))
		p2query = db.queryOne("""SELECT id FROM players WHERE tag=?""",((p2,)))
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

			row = db.queryOne("""SELECT display_tag FROM players WHERE id=?""", (player_1_id,))
			head2headDictionary["player_1_tag"] = row[0]
			row = db.queryOne("""SELECT display_tag FROM players WHERE id=?""", (player_2_id,))
			head2headDictionary["player_2_tag"] = row[0]

			rows = db.queryMany("""SELECT tournaments.name, tournaments.id, tournaments.calendar_date, winners.id, losers.id, winners.tag, losers.tag, winners.display_tag, losers.display_tag, sets.* FROM sets
					inner join players AS winners on sets.winner_id = winners.id
					inner join players AS losers on sets.loser_id = losers.id
					inner join tournaments on sets.db_tournament_id = tournaments.id
					WHERE (winners.id=? and losers.id=?)
					OR (winners.id=? and losers.id=?)
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
				winner_display_tag = row[7]
				loser_display_tag = row[8]
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
							VALUES(?,?,?,?,?,?)""",
							submit_tuple)

			message = "Your concern was successfully submitted! We hear you loud and clear and we'll look in to fixing this issue."
		except: 
			message = "Your concern is important to us but could not be submitted at this time. Please try again!"
		finally:
			return render_template("submit_form.j2", message=message)

#put this behind some kind of login credentials
@app.route('/submit/list')
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
	app.run()










