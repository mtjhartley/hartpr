import challonge
import trueskillapi
from fuzzywuzzy import fuzz, process
from operator import itemgetter
import sqlite3 
import sys
import datetime
import re
import json
import os
import database


database.get_db()

def set_credentials(user):
	if os.environ.has_key(user):
		challonge.set_credentials(user, os.environ[user])
	else:
		challonge.set_credentials(user, json.loads(open("./credentials.json").read())[user])

set_credentials("hartlax")
set_credentials("gameworksseattle")
set_credentials("epeengaming")

def get_all_the_sets(tourneyURL):
	list_of_sets = challonge.matches.index(tourneyURL)
	return list_of_sets

def get_all_sponsors():
	sponsors = []
	rows = database.queryMany("""SELECT sponsor from sponsors;""")
	for row in rows:
		sponsors.append(row[0])
	return sponsors

def bracket_sponsor_remover(list_of_player_tags):
	bracket_removed_list = []
	for tag in list_of_player_tags:
		if type(tag) == int:
			print tag
		try: 
			removed_parenthesis_tag = re.sub((r'\(.*?\)'), '', tag)
			removed_square_brackets_tag = re.sub((r'\[.*?\]'), '', removed_parenthesis_tag)
			bracket_removed_list.append(removed_square_brackets_tag)
		except TypeError:
			bracket_removed_list.append(str(tag))
	return bracket_removed_list

def sponsor_remover(tag, sponsors_list):
	print "input tag:", tag
	periodCount = tag.count(".")
	lineCount = tag.count("|")
	spaceCount = tag.count(" ")
	underscoreCount = tag.count("_")

	if periodCount and lineCount:
		noperiodtag = tag.replace('.', ' . ', 1)
		nospacetaglist = tag.split('.')
		nospacetag = " ".join(nospacetaglist)
		nolinetag = nospacetag.replace("|", " | ", 1)
		nolinetaglist = nospacetag.split("|")

		final_list = []
		for word in nolinetaglist:
			nospace = word.strip
			final_list.append(word.strip())

		if final_list[0].lower() in sponsors_list:
			print "Sponsor detected:", final_list[0]
			return " ".join(final_list[1:])
		else:
			print "No sponsor detected..."
			return tag

	if periodCount or lineCount or underscoreCount:
		if periodCount:
			print "Period . detected."
			striptag = tag.replace('.', ' . ', 1)
		if lineCount:
			print "Line | detected."
			striptag = tag.replace('|', ' | ', 1)
		if underscoreCount:
			print "Underscore _ detected"
			striptag = tag.replace('_', ' _ ', 1)

		nospacetaglist = striptag.split()
		for i in range(len(nospacetaglist)):
			if nospacetaglist[i] == (".") or nospacetaglist[i] == ("|") or nospacetaglist[i] == ('_'):
				if nospacetaglist[0].lower() in sponsors_list:
					final_list = nospacetaglist[i+1:]
					return " ".join(final_list)
				else:
					print "No sponsor found."
					return tag

	if spaceCount > 1:
		print "Multiple spaces detected"
		nospacetaglist = tag.split()
		if nospacetaglist[0].lower() in sponsors_list:
			return " ".join(nospacetaglist[1:])

	zerospacetaglist = tag.split()
	if spaceCount and zerospacetaglist[0].lower() in sponsors_list:
		print "Sponsor detected."
		return " ".join(zerospacetaglist[1:])
	else:
		print "No sponsor found for", tag
		return tag

def create_stripped_sponsor_list(player_list, loweredSponsors):
	stripped_sponsor_list = []
	print "printing player_list"
	print player_list
	for tag in player_list:
		stripped_tag = sponsor_remover(tag, loweredSponsors)
		stripped_sponsor_list.append(stripped_tag)
	return stripped_sponsor_list

def create_db_tag_list_for_comparison():
	database_tag_list = []
	rows = database.queryMany("SELECT tag FROM players")

	for row in rows:
		database_tag_list.append((row[0]))

	return database_tag_list

def fuzzy_string_match_ratio(tourney_tag_list, db_tag_list):
	dictionary_of_string_matches = {}

	for tourney_tag in tourney_tag_list:
		similar_tags = []
		for database_tag in db_tag_list:
			similar_ratio = fuzz.ratio(tourney_tag.decode('utf-8', 'ignore'), database_tag.decode('utf-8', 'ignore'))
			float_len_db_tag_minus = float(len(database_tag)) - 1
			float_len_db_tag = float(len(database_tag))
			threshold_ratio = float_len_db_tag_minus / float_len_db_tag * 100 - 1

			if re.sub(' ', '', tourney_tag.decode('utf-8', 'ignore')) == re.sub(' ', '', database_tag.decode('utf-8', 'ignore')):
				similar_tags.append((database_tag, similar_ratio, "tag ratio", "100%"))
			elif similar_ratio > threshold_ratio and tourney_tag != database_tag and threshold_ratio != -1.0:
				similar_tags.append((database_tag, similar_ratio, "threshold ratio", threshold_ratio))
			else:
				if similar_ratio > 90 and tourney_tag != database_tag:
					similar_tags.append((database_tag, similar_ratio, "threshold ratio", similar_ratio)) 

		dictionary_of_string_matches[tourney_tag] = sorted(similar_tags, key = itemgetter(1), reverse = True)
	return dictionary_of_string_matches

def confirm_or_deny_existing_player(tourney_tag_list, dictionary_of_string_matches):
	new_tourney_tag_list = []
	for player in tourney_tag_list:
		if dictionary_of_string_matches[player] and dictionary_of_string_matches[player][0][3] == "100%":
			print "Player tag in tournament:", player
			print "The database found a tag match: " + '"' + str(dictionary_of_string_matches[player][0][0]) + '"' + " with a fuzz.ratio of " + str(dictionary_of_string_matches[player][0][1])
			print "Adding the player to the list with complete certainty!"
			print 
			new_tourney_tag_list.append((dictionary_of_string_matches[player][0][0], True))
		elif dictionary_of_string_matches[player]:
			print "Player tag in tournament:", player
			count = 0
			for option_number in range(len(dictionary_of_string_matches[player])):
				count += 1 
				print "There are " + str(len(dictionary_of_string_matches[player])) + " potential matches."
				print "The database found a tag match: " + '"' + str(dictionary_of_string_matches[player][option_number][0]) + '"' + " with a fuzz.ratio of " + str(dictionary_of_string_matches[player][option_number][1])
				var = raw_input("Are these the same player? Type Y/N, or override by typing 'override' and then the player's tag in the database.\n")
				if var.lower() == "y" or var.lower() == "yes":
					print "Tournament list was updated with the correct tag."
					new_tourney_tag_list.append((dictionary_of_string_matches[player][option_number][0], True))
					print
					break
				elif var.lower() == 'n' or var.lower() == "no" and count == (len(dictionary_of_string_matches[player]) -1):
					print "Keep looping!"
				elif var.lower().strip() == "override":
					new_var = raw_input("Please type the known tag in lowercase: \n") #override function?
					new_tourney_tag_list.append((new_var, True))
					break
				elif count == len(dictionary_of_string_matches[player]):
					print "No matches confirmed"
					new_tourney_tag_list.append((player, False))
					print
				else:
					"Let's try again with the next option."
		else:
			print "Player tag in tournament:", player
			print "No matches for " + player + " were found in the database."
			var = raw_input("Would you like to override this entry with a new tag? \n")
			if var.lower() == "no" or var.lower() == "n" or var.lower() == "":
				new_tourney_tag_list.append((player, False))
			else:
				new_tourney_tag_list.append((var.lower(), True))
	print "Tourney Tag List Successfully Updated!"
	print "The length of the old list was", len(tourney_tag_list)
	print "The length of the new list is", len(new_tourney_tag_list)
	print "The old list was ", tourney_tag_list
	print "The new list is ", new_tourney_tag_list
	prompt = raw_input("Are all of these changes correct? Database will be updated. \nPlease type 'Yes, all of these changes are correct.'\n")
	if prompt.lower() == "Yes, all of these changes are correct." or prompt.lower() == "yes":
		pass
	else:
		"Please confirm all changes are correct, exiting program."
		sys.exit()
	return new_tourney_tag_list

def check_for_alternate_tags(final_tag_list):
	shin_final_tag_list = []
	alternate_tags_dict = {}
	rows = database.queryMany("SELECT alt_tag, db_player_id FROM alternate_tags")

	for row in rows:
		alternate_tags_dict[row[0].lower().strip()] = row[1]
	print alternate_tags_dict
	for final_tag in final_tag_list:
		if not final_tag[1] and (final_tag[0] in alternate_tags_dict.keys()):
			player_id = alternate_tags_dict[final_tag[0]]
			row = database.queryOne("SELECT tag FROM players WHERE id= %s", (player_id,))

			print "row", row
			print "row[0]", row[0]
			final_tag = (row[0], True)
			shin_final_tag_list.append(final_tag)	
		else:
			shin_final_tag_list.append(final_tag)
	print "shin_final_tag_list", shin_final_tag_list
	return shin_final_tag_list

def update_entrant_id_to_player_id_dict_and_player_database(list_of_player_tags, final_tag_list, challonge_player_dicts):
	entrant_id_to_player_id_dict = {}


	for player_dict in challonge_player_dicts:
		print "currently in this dict", player_dict["name"]
		for original_challonge_tag, updated_database_tag in zip(list_of_player_tags, final_tag_list):
			if original_challonge_tag == player_dict["name"]:
				entrant_id = player_dict["id"]

				rows = database.queryMany("SELECT * FROM players WHERE tag=%s", (updated_database_tag[0],))
				print "printing rows for update entrant id func"
				print rows


				if (len(rows) < 1) and not updated_database_tag[1]:
					print "inserting"
					tag = str(updated_database_tag[0].lower())
					display_tag = str(player_dict['name'])
					trueskill_mu = trueskillapi.defaultRating.mu 
					trueskill_sigma = trueskillapi.defaultRating.sigma 
					state = "WA"
					player_tuple = (tag, display_tag, trueskill_mu, trueskill_sigma, state)
					cur = database.queryInsertNoRow("INSERT INTO players(tag, display_tag, trueskill_mu, trueskill_sigma, location) VALUES (%s, %s, %s, %s, %s) RETURNING id;", player_tuple)
					id_of_new_row = cur.fetchone()[0]
					entrant_id_to_player_id_dict[entrant_id] = id_of_new_row

				elif (len(rows) == 1):
					entrant_id_to_player_id_dict[entrant_id] = rows[0][0]
				else:
					print ("multiple tags for tag: {}".format((updated_database_tag[0],)))
					print rows


	return entrant_id_to_player_id_dict 

def scoreSplit(score_csv):
	count = 0
	dashCount = score_csv.count("-")
	for i in range(len(score_csv)):
		count += 1
		if dashCount == 1 and score_csv[i] == '-':
			score_tuple = (score_csv[:i], score_csv[i+1:])
			return score_tuple
		if dashCount == 2 and count > 1 and score_csv[i] == '-':
			score_tuple = (score_csv[:i], score_csv[i+1:])
			return score_tuple

def finalize_sets_with_updated_winner_loser_id_and_score(entrant_id_to_player_id_dict, tournament_list_of_sets):
	print entrant_id_to_player_id_dict
	for a_set in tournament_list_of_sets:
		winner = a_set["winner_id"]
		loser = a_set["loser_id"]


		a_set["database_winner_id"] = entrant_id_to_player_id_dict[winner]
		a_set["database_loser_id"] = entrant_id_to_player_id_dict[loser]


		score_csv = str(a_set['scores_csv'])
		a_set['set_scores_tuple'] = scoreSplit(score_csv)
	return tournament_list_of_sets

def create_list_of_set_data_in_tuple(finalized_set_list):
	list_of_set_data_in_tuples = []
	for a_set in finalized_set_list:
		database_winner_id = a_set["database_winner_id"]
		database_loser_id = a_set["database_loser_id"]
		if a_set["winner_id"] == a_set["player1_id"]:
			try:
				winner_score = a_set["set_scores_tuple"][0]
				loser_score = a_set["set_scores_tuple"][1] 
			except TypeError:
				winner_score = None
				loser_score = None
		elif a_set["winner_id"] == a_set["player2_id"]:
			try: 
				winner_score = a_set["set_scores_tuple"][1]
				loser_score = a_set["set_scores_tuple"][0]
			except TypeError:
				winner_score = None
				loser_score = None
		set_id = "c'" + str(a_set["id"])
		bracket_id = a_set['group_id']
		unique_tournament_id = a_set["tournament_id"] 
		phase = a_set['identifier']
		set_tuple = (database_winner_id, database_loser_id, winner_score, loser_score, set_id, bracket_id, unique_tournament_id, phase)
		list_of_set_data_in_tuples.append(set_tuple)
	return list_of_set_data_in_tuples

def create_challonge_tourney_data_in_tuple(tourneyURL, subdomain=None):
	if subdomain:
		subdomain = subdomain
	else:
		subdomain = None
	tournament = challonge.tournaments.show(tourneyURL)
	name = tournament["name"]
	url = tournament["url"]
	whole_url = tournament["full_challonge_url"]
	start_date_object = (tournament['started_at'])
	start_date_obj =  datetime.datetime.date(start_date_object)
	start_date = start_date_obj.isoformat()
	unique_tournament_id = int(tournament['id'])
	website = "challonge"
	tournament_tuple = (name, url, start_date, unique_tournament_id, website, subdomain)
	return tournament_tuple

def update_rankings_for_challonge_tournament(tourneyURL, subdomain=None):
	if subdomain:
		tourneyURL = subdomain + "-" + tourneyURL
	list_of_all_sets = get_all_the_sets(tourneyURL)
	challonge_player_dicts = challonge.participants.index(tourneyURL)
	list_of_player_tags = map(lambda dictionary: dictionary["name"], challonge_player_dicts)
	sponsors = get_all_sponsors()
	loweredSponsors = map(lambda string: string.lower(), sponsors)
	no_bracket_tag_list = bracket_sponsor_remover(list_of_player_tags)
	stripped_sponsor_list = create_stripped_sponsor_list(no_bracket_tag_list, loweredSponsors)
	lowered_stripped_sponsor_list = map(lambda string: string.lower(), stripped_sponsor_list)
	db_tag_list = create_db_tag_list_for_comparison()
	dictionary_of_close_matches_from_tournament_and_database = fuzzy_string_match_ratio(lowered_stripped_sponsor_list, db_tag_list)
	final_tag_list = confirm_or_deny_existing_player(lowered_stripped_sponsor_list, dictionary_of_close_matches_from_tournament_and_database)
	shin_final_tag_list = check_for_alternate_tags(final_tag_list)
	entrant_id_to_player_id_dict = update_entrant_id_to_player_id_dict_and_player_database(list_of_player_tags, shin_final_tag_list, challonge_player_dicts)
	print entrant_id_to_player_id_dict
	finalized_sets_with_db_id_and_scores = finalize_sets_with_updated_winner_loser_id_and_score(entrant_id_to_player_id_dict, list_of_all_sets)
	list_of_set_tuples = create_list_of_set_data_in_tuple(finalized_sets_with_db_id_and_scores)
	challonge_tournament_data_tuple = create_challonge_tourney_data_in_tuple(tourneyURL, subdomain)
	boole = database.update_database_with_tournament_information(challonge_tournament_data_tuple)
	if boole:
		database.update_database_with_set_information(list_of_set_tuples)
		trueskillDictionary = database.create_trueskill_dictionary_for_tournament(entrant_id_to_player_id_dict)
		trueskillapi.update_trueskills(list_of_set_tuples, trueskillDictionary)
		database.update_player_database_with_new_trueskill(trueskillDictionary)
		print "Update complete!"
	else:
		print "Tournament already in the database."


#update_rankings_for_challonge_tournament("tuk324")
#update_rankings_for_challonge_tournament("ESSM10M")
#update_rankings_for_challonge_tournament("tuk930")


