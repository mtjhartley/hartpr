from jinja2 import Template
import sqlite3

playerRankingDictionary = {}
playerRankingDictionary["players"] = []
con = sqlite3.connect("src/ctest1smashggperfect.db")
with con:
	cur = con.cursor()
	cur.execute("""SELECT tag, display_tag, Round((trueskill_mu-3*trueskill_sigma),3) AS weighted_trueskill 
				FROM players 
				WHERE players.location = 'WA' 
				ORDER BY weighted_trueskill desc;
				""")
	rows = cur.fetchall()
	count = 0
	for row in rows:
		count += 1
		display_tag, weighted_trueskill = row[1], row[2]
		player_tuple = (count, display_tag, weighted_trueskill)

		playerRankingDictionary["players"].append(player_tuple)


tournamentDictionary = {}
tournamentDictionary["tournaments"] = []
with con:
	cur = con.cursor()
	cur.execute("""SELECT name, website, url, calendar_date
				FROM tournaments
				ORDER BY calendar_date DESC;
				""")
	rows = cur.fetchall()
	for row in rows:
		name = row[0]
		website = str("https://www." + row[1] + ".com/" + row[2])
		calendar_date = row[3]
		tournament_tuple = (name, website, calendar_date)
		tournamentDictionary["tournaments"].append(tournament_tuple)



dempseySetsDictionary = {}
dempseySetsDictionary["sets"] = []
with con:
	cur = con.cursor()
	cur.execute("""SELECT tournaments.name, tournaments.calendar_date, winners.tag, losers.tag, sets.* FROM sets
				inner join players AS winners on sets.winner_id = winners.id
				inner join players AS losers on sets.loser_id = losers.id
				inner join tournaments on sets.db_tournament_id = tournaments.id
				WHERE (winners.tag = 'dempsey' or losers.tag = 'dempsey')
				AND winner_score != -1 AND loser_score != -1
				ORDER BY calendar_date DESC;
				""")

	rows = cur.fetchall()
	for row in rows:
		tournament_name = row[0]
		if row[2] == 'dempsey':
			opponent_tag = row[3]
			result = "W"
		else:
			opponent_tag = row[2]
			result = "L"
		calendar_date = row[1]
		set_tuple = (tournament_name, opponent_tag, result, calendar_date)
		dempseySetsDictionary["sets"].append(set_tuple)



def generateAnyoneSetsDictionary(player_tag, player_id, player_display_tag, playerSetDictionary):
	setsDictionary = {}
	setsDictionary["sets"] = []
	setsDictionary["id"] = player_id


	with con:
		player_tuple = (player_tag, player_tag)
		cur = con.cursor()
		cur.execute("""SELECT tournaments.name, tournaments.calendar_date, winners.tag, losers.tag, winners.display_tag, losers.display_tag, sets.* FROM sets
				inner join players AS winners on sets.winner_id = winners.id
				inner join players AS losers on sets.loser_id = losers.id
				inner join tournaments on sets.db_tournament_id = tournaments.id
				WHERE (winners.tag=? or losers.tag=?)
				AND winner_score != -1 AND loser_score != -1
				ORDER BY calendar_date DESC;
				""", player_tuple)

		rows = cur.fetchall()
		for row in rows:
			tournament_name = row[0]
			if row[2] == player_tag:
				opponent_tag = row[5]
				result = "W"
				winner_score = row[9]
				loser_score = row[10]
			else:
				opponent_tag = row[4]
				result = "L"
				loser_score = row[9]
				winner_score = row[10]
			calendar_date = row[1]
			score_string = str(winner_score) + '-' + str(loser_score)
			set_tuple = (tournament_name, opponent_tag, result, calendar_date, score_string)
			setsDictionary["sets"].append(set_tuple)
			setsDictionary["display_name"] = player_display_tag
		cur.execute("""SELECT trueskill_mu, trueskill_sigma, (trueskill_mu-3*trueskill_sigma) as weighted_trueskill
					FROM players
					WHERE tag=?""", (player_tag,))
		rows = cur.fetchall()
		for row in rows:
			mu = row[0]
			sigma = row[1]
			weighted_trueskill = row[2]
			setsDictionary["mu"] = round(mu, 3)
			setsDictionary["sigma"] = round(sigma, 3)
			setsDictionary["weighted_trueskill"] = round(weighted_trueskill, 3)

	player = player_tag.encode('utf-8')
	playerSetDictionary[player] = setsDictionary

def getAllPlayersTagsAndIds():
	player_list = []
	with con:
		cur = con.cursor()
		cur.execute("SELECT tag, id, display_tag from players")
		rows = cur.fetchall()
		player_list = map(lambda row: (row[0], row[1], row[2]), rows)
	return player_list

database_players = getAllPlayersTagsAndIds()


def generate_everyone_sets_dictionary(players):
	playerSetDictionary = {}
	for player in players:
		generateAnyoneSetsDictionary(player[0], player[1], player[2], playerSetDictionary)
	return playerSetDictionary


allPlayersSetDictionary = generate_everyone_sets_dictionary(database_players)

def addPlayerNameAsKeyValue(allPlayersSetDictionary):
	for player in allPlayersSetDictionary:
		allPlayersSetDictionary[player]["name"] = player
	return allPlayersSetDictionary

final_dict = addPlayerNameAsKeyValue(allPlayersSetDictionary)

fuckup_count = 0
fuckupstag = []
fuckupsdisplaytag = []

for player in final_dict:
	try: 
		wf = open("html/{}.html".format(final_dict[player]["id"]), "w+")
		wf.write(Template(open("templates/player.j2", "r").read()).render(final_dict[player]).encode("utf-8"))
	except UnicodeEncodeError:
		print "fuck you faggot"
		print "i'm a fucking legend"

tournamentWebPageDictionary = {}
tournamentWebPageDictionary["players"] = []
tournamentWebPageDictionary["sets"] = []
tournamentWebPageDictionary["information"] = {}
with con:
	cur = con.cursor()
	cur.execute("""SELECT * FROM tournaments
				WHERE name = 'Dairly Beloved';
				""")
	rows = cur.fetchall()
	for row in rows:
		tourney_id = row[0]
		name = row[1]
		url = "www." + row[5] + ".com/" + row[2]
		calendar_date = row[3]
		tournamentWebPageDictionary["information"]["tourney_id"] = tourney_id
		tournamentWebPageDictionary["information"]["name"] = name
		tournamentWebPageDictionary["information"]["url"] = url
		tournamentWebPageDictionary["information"]["calendar_date"] = calendar_date
	cur.execute("""SELECT winners.display_tag, losers.display_tag, sets.* FROM sets 
				INNER JOIN players as winners on sets.winner_id = winners.id
				INNER JOIN players as losers on sets.loser_id = losers.id
				WHERE db_tournament_id=?""", (tourney_id,))
	rows = cur.fetchall()
	for row in rows:
		winner = row[0]
		loser = row[1]
		winner_score = row[5]
		loser_score = row[6]
		print winner_score
		print loser_score
		if (winner_score == None and loser_score == None):
			score_string = "Unreported"
		elif winner_score == -1 or loser_score == -1:
			score_string = "DQ"
		score_string = str(winner_score) + '-' + str(loser_score)
		set_tuple = (winner, loser, score_string)
		tournamentWebPageDictionary["sets"].append(set_tuple)
		if winner not in tournamentWebPageDictionary["players"] and loser not in tournamentWebPageDictionary["players"]:
			tournamentWebPageDictionary["players"].append(winner)
	tournamentWebPageDictionary["players"].sort()

print tournamentWebPageDictionary

wf = open("html/dairlybelovedTest.html", "w+")
wf.write(Template(open("templates/dairlybelovedTest.j2", "r").read()).render(tournamentWebPageDictionary).encode("utf-8"))



"""
for player in final_dict:
	try: 
		wf = open("html/{}.html".format(final_dict[player]["id"]), "w+")
		#final_dict[player]["name"] = final_dict[player]["name"].decode('utf-8')

		wf.write(Template(open("templates/dempseySets.j2", "r").read()).render(final_dict[player]))

	except UnicodeEncodeError:
		#final_dict[player]["name"] = final_dict[player]["name"].encode('utf-8')
		#final_dict[player]["name"] = final_dict[player]["name"].decode('ascii', 'ignore')
		print type(final_dict[player]["name"])
		fuckup_count += 1



		wf = open("html/{}.html".format(final_dict[player]["id"]), "w+")
		wf.write(Template(open("templates/dempseySets.j2", "r").read()).render(final_dict[player]).encode("utf-8"))
		fuckupstag.append(final_dict[player]["name"])
		fuckupsdisplaytag.append(final_dict[player]["display_name"])

		pass


for fuckup in fuckupstag:
	print final_dict[fuckup]
print fuckupstag
print fuckupsdisplaytag
"""
"""for fuckup in fuckups:
	print fuckup.decode('ascii', 'ignore')
	print fuckup.decode('ascii', 'replace')
	#print fuckup.encode("utf-8")
	
	#print fuckup.encode('ascii')
print fuckup_count"""

#http://stackoverflow.com/questions/22181944/using-utf-8-characters-in-a-jinja2-template




#9 failed because of this error...unacceptable lmfao
#print playerRankingDictionary
#print tournamentDictionary
#print dempseySetsDictionary


testObj = {
	"players": [(1, "dz", 57.5), (2, "dempsey", 25), (3, "chevy", -10000), (4, "almond", -1000000)]}

wf = open("html/playertest.html", "w+")
wf.write(Template(open("templates/playertest.j2", "r").read()).render(playerRankingDictionary).encode("utf-8"))


wt = open("html/tournamenttest.html", "w+")
wt.write(Template(open("templates/tournamenttest.j2", "r").read()).render(tournamentDictionary))


"""wd = open("html/dempseySets.html", "w+")
wd.write(Template(open("templates/dempseySets.j2", "r").read()).render(dempseySetsDictionary))"""

print('Generation Complete')


