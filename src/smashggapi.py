import pysmash
import trueskillapi
import sqlite3
import datetime
import urllib, json
import database



smash = pysmash.SmashGG()

def get_all_the_sets(tourneyName, eventName):
	brackets = smash.tournament_show_event_brackets(tourneyName, eventName)
	melee_singles_bracket_ids = brackets["bracket_ids"]
	print melee_singles_bracket_ids

	list_of_all_sets = []
	for list_of_sets_for_a_pool in melee_singles_bracket_ids:
		list_of_all_sets.append(smash.bracket_show_sets(list_of_sets_for_a_pool))

	return list_of_all_sets


def create_gamertag_to_sggplayerid_dict(tourneyName):
	brackets = smash.tournament_show_event_brackets(tourneyName, "melee-singles")
	melee_singles_bracket_ids = brackets["bracket_ids"]
	gamertag_to_sggplayerid_dict = {}
	print melee_singles_bracket_ids
	for bracket_id in melee_singles_bracket_ids:
		url = "https://api.smash.gg/phase_group/{0}{1}".format(bracket_id, "?expand[]=entrants")
		print url

		response = urllib.urlopen(url)
		attendees = json.loads(response.read())

		if attendees['entities']['groups']['state'] == 1: #not started! 
			melee_singles_bracket_ids.remove(bracket_id)
		else:
			for player in attendees['entities']['player']:
				gamertag = player['gamerTag']
				sgg_player_id = player['id']
				gamertag_to_sggplayerid_dict[gamertag] = sgg_player_id
	return gamertag_to_sggplayerid_dict



def update_entrant_id_to_player_id_dict_and_player_database(tourneyName, eventName, gamertag_to_sggplayerid_dict):
	entrant_id_to_player_id_dict = {}

	tourney_players = smash.tournament_show_players(tourneyName, eventName)
	#doesn't work with BRACKETS THAT HAVE NOBODY IN THEM
	print "length of tourney players is ", len(tourney_players)
	print "length of ditionarykeys is ", len(gamertag_to_sggplayerid_dict.keys())


	for bracket_player in tourney_players:
		entrant_id = (bracket_player["entrant_id"])
		tag = bracket_player["tag"].lower()
		tag_tuple = (tag,)
		sgg_player_id = gamertag_to_sggplayerid_dict[bracket_player["tag"]]
		rows = database.queryMany("SELECT * FROM players WHERE sgg_player_id=%s", (sgg_player_id,))
		
		if (len(rows) < 1):
			tag = (bracket_player["tag"].lower())
			display_tag = (bracket_player["tag"])
			fname = (bracket_player["fname"])
			lname = (bracket_player["lname"])
			location = str(bracket_player["state"])
			trueskill_mu = trueskillapi.defaultRating.mu 
			trueskill_sigma = trueskillapi.defaultRating.sigma 
			sgg_player_id = gamertag_to_sggplayerid_dict[display_tag]
			player_tuple = (tag, display_tag, fname, lname, location, trueskill_mu, trueskill_sigma, sgg_player_id)
			print player_tuple
			cur = database.queryInsertNoRow("INSERT INTO players(tag, display_tag, fname, lname, location, trueskill_mu, trueskill_sigma, sgg_player_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;", player_tuple)
			print "printing cur?"
			print cur
			id_of_new_row = cur.fetchone()[0]
			entrant_id_to_player_id_dict[entrant_id] = id_of_new_row

		elif (len(rows) == 1):
			entrant_id_to_player_id_dict[entrant_id] = rows[0][0]

		else:
			print("Multiple Tags for tag: {}".format(tag_tuple))

	return entrant_id_to_player_id_dict 


def update_sets_with_winner_and_loser_ids_using_a_list(entrant_id_to_player_id_dict, tournament_list_of_sets):
	for a_list_of_sets_in_a_bracket in tournament_list_of_sets:
		for a_set in a_list_of_sets_in_a_bracket:
			winner = a_set["winner_id"]
			loser = a_set["loser_id"]
			try:
				a_set["database_winner_id"] = entrant_id_to_player_id_dict[int(winner)]
				a_set["database_loser_id"] = entrant_id_to_player_id_dict[int(loser)]
			except KeyError:
				pass
	return tournament_list_of_sets

def create_list_of_set_data_in_tuple(tournament_info, updated_set_list):
	list_of_set_data_in_tuples = []
	for a_set in updated_set_list:
		print "len all sets again above"
		try:
			database_winner_id = a_set["database_winner_id"]
			database_loser_id = a_set["database_loser_id"]
		except KeyError:
			database_winner_id = None 
			database_loser_id = None 
		if a_set['winner_id'] == a_set['entrant_1_id']:
			winner_score = a_set['entrant_1_score'] 
			loser_score = a_set['entrant_2_score'] 
		elif a_set['winner_id'] == a_set['entrant_2_id']:
			winner_score = a_set['entrant_2_score']
			loser_score = a_set['entrant_1_score']
		set_id = "sgg'" + str(a_set['id'])
		bracket_id = a_set["bracket_id"]
		unique_tournament_id = tournament_info['tournament_id']
		phase = a_set['short_round_text']
		set_tuple = (database_winner_id, database_loser_id, winner_score, loser_score, set_id, bracket_id, unique_tournament_id, phase)
		print set_tuple
		list_of_set_data_in_tuples.append(set_tuple)
	return list_of_set_data_in_tuples

def create_sgg_tourney_data_in_tuple(tournament_info):
	name = tournament_info['name']
	url = tournament_info['tournament_full_source_url']
	whole_url = "https://www.smash.gg/" + tournament_info["bracket_full_source_url"]
	start_date_unix = tournament_info['start_at']
	start_date_object = datetime.date.fromtimestamp(start_date_unix)
	start_date = start_date_object.isoformat()
	unique_tournament_id = tournament_info['tournament_id']
	website = "smashgg"
	tournament_tuple = (name, url, start_date, unique_tournament_id, website, None)
	return tournament_tuple


def create_trueskill_dictionary_for_tournament(tourneyName, eventName):
	trueskillDictionary = {}
	entrant_id_to_player_id_dict = update_entrant_id_to_player_id_dict_and_player_database(tourneyName, eventName)

	for player in entrant_id_to_player_id_dict:
		db_id = entrant_id_to_player_id_dict[player]
		db_id_tuple = (db_id,)
		row = database.queryOne("SELECT trueskill_mu, trueskill_sigma FROM players WHERE id=?", db_id_tuple)
		trueskill_list = []
		trueskill_list.append(row)
		trueskillDictionary[db_id] = trueskill_list
	return trueskillDictionary

def update_rankings_for_smashgg_tournament(tourneyName, bracketName):
	tournament_info = smash.tournament_show_with_brackets(tourneyName, bracketName)
	list_of_all_sets = get_all_the_sets(tourneyName, bracketName)
	gamertag_to_sggplayerid_dict = create_gamertag_to_sggplayerid_dict(tourneyName)
	entrant_id_to_player_id_dict = update_entrant_id_to_player_id_dict_and_player_database(tourneyName, bracketName, gamertag_to_sggplayerid_dict)
	all_sets_updated_list = update_sets_with_winner_and_loser_ids_using_a_list(entrant_id_to_player_id_dict, list_of_all_sets)
	all_sets = [one_set for one_pool in all_sets_updated_list for one_set in one_pool]
	list_of_set_data_in_tuple = create_list_of_set_data_in_tuple(tournament_info, all_sets)
	sgg_tournament_data_tuple = create_sgg_tourney_data_in_tuple(tournament_info)
	boole = database.update_database_with_tournament_information(sgg_tournament_data_tuple)
	if boole:
		database.update_database_with_set_information(list_of_set_data_in_tuple)
		trueskillDictionary = database.create_trueskill_dictionary_for_tournament(entrant_id_to_player_id_dict)
		trueskillapi.update_trueskills(list_of_set_data_in_tuple, trueskillDictionary)
		database.update_player_database_with_new_trueskill(trueskillDictionary)
		print "Update complete!"
	else:
		print "Tournament already in the database."









'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''


'''currently useless if we give default trueskill to new players in db, as I have in
the update_entrant_id_to_player_id_dict_and_player_database function'''
def set_default_trueskill_to_new_players(trueskillDictionary, bracket_ids):
	for bracket_id in bracket_ids:
		players_in_bracket = smash.bracket_show_players(bracket_id)
		for player in players_in_bracket:
			if trueskillDictionary.has_key(player['tag']):
				pass
			else:
				trueskillDictionary[player['tag'].lower()] = trueskillapi.defaultRating