def update_database_with_tournament_information(tourney_data_in_tuple):
	con = sqlite3.connect("ctest1smashggperfect.db")
	with con:
		cur = con.cursor()
		try:	
			cur.execute("INSERT INTO tournaments (name, url, calendar_date, unique_tournament_id, website, subdomain) VALUES(?,?,?,?,?,?);", tourney_data_in_tuple)
			return True
		except sqlite3.IntegrityError:
			print "Did not add duplicate tournament to database."
			return False
	con.close()


def update_database_with_set_information(list_of_set_data_in_tuples):
	con = sqlite3.connect("ctest1smashggperfect.db")
	with con:
		cur = con.cursor()
		unique_tournament_id = list_of_set_data_in_tuples[0][6]
		try:
			cur.execute("SELECT id FROM tournaments WHERE unique_tournament_id=?", (unique_tournament_id,))
			#what if they overlap b/w challonge and sgg?
			#sort the table to do the most RECENT so when sgg catches up to challonge it's not a problem
			#unique tournament id is helpful for finding, but do we need it in the db twice? ...gut tells me no
			#can delete it and foreign key with teh other shit once we find this id number. 
			rows = cur.fetchone()
			db_tourney_id = rows[0] #integer, tournament id for db
			new_list_of_set_data_in_tuples = []
		    #set_tuple = (database_winner_id, database_loser_id, winner_score, loser_score, set_id, bracket_id, unique_tournament_id, phase) unique is index 6
			for tuple_data in list_of_set_data_in_tuples:
				new_tuple = (tuple_data[0], tuple_data[1], tuple_data[2], tuple_data[3], tuple_data[4], tuple_data[5], tuple_data[7])
				new_tuple = new_tuple + (db_tourney_id,)
				new_list_of_set_data_in_tuples.append(new_tuple)
			#change to reflect adding set_id (text) unique to challonge or sgg set. 
			cur.executemany("INSERT INTO sets(winner_id, loser_id, winner_score, loser_score, set_id, bracket_id, phase, db_tournament_id) VALUES (?,?,?,?,?,?,?,?)", new_list_of_set_data_in_tuples)

			print "Sets were successfully added to the database"
		except sqlite3.IntegrityError:
			print "Duplicate sets were not added to the database."
	con.close()


#can just pass this the dictionary motha fucka so it works for both Kreygasm
def create_trueskill_dictionary_for_tournament(entrant_to_player_dict):
	trueskillDictionary = {}
	con = sqlite3.connect("ctest1smashggperfect.db")
	with con:
		cur = con.cursor()
		for player in entrant_to_player_dict:
			db_id = entrant_to_player_dict[player]
			db_id_tuple = (db_id,)
			cur.execute("SELECT trueskill_mu, trueskill_sigma FROM players WHERE id=?", db_id_tuple)
			rows = cur.fetchone()
			trueskill_list = []
			for row in rows:
				trueskill_list.append(row)
			#print "printing db call"
			#print rows
			#print "type rows", type(rows) #tuple
			trueskillDictionary[db_id] = trueskill_list

	con.close()
	return trueskillDictionary

def update_player_database_with_new_trueskill(trueskillDictionary):
	con = sqlite3.connect("ctest1smashggperfect.db")
	with con:
		cur = con.cursor()
		list_of_db_player_ids = trueskillDictionary.keys()
		for db_player_id in list_of_db_player_ids:
			new_trueskill_list = trueskillDictionary[db_player_id]
			new_trueskill_list.append(db_player_id)
			new_trueskill_mu = new_trueskill_list[0]
			new_trueskill_sigma = new_trueskill_list[1]
			update_tuple = (new_trueskill_list[0], new_trueskill_list[1], db_player_id)
			cur.execute("UPDATE players SET trueskill_mu=?, trueskill_sigma=? WHERE id=?", update_tuple)
	con.close()





#new main.py ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



def update_rankings_for_smashgg_tournament(tourneyName, bracketName): #db parameter? makes sense...lol
	tournament_info = smashggapi.smash.tournament_show_with_brackets(tourneyName, bracketName)
	list_of_all_sets = smashggapi.get_all_the_sets(tourneyName, bracketName)
	gamertag_to_sggplayerid_dict = smashggapi.create_gamertag_to_sggplayerid_dict(tourneyName)
	entrant_id_to_player_id_dict = smashggapi.update_entrant_id_to_player_id_dict_and_player_database(tourneyName, bracketName, gamertag_to_sggplayerid_dict)
	all_sets_updated_list = smashggapi.update_sets_with_winner_and_loser_ids_using_a_list(entrant_id_to_player_id_dict, list_of_all_sets)
	all_sets = [one_set for one_pool in all_sets_updated_list for one_set in one_pool]
	list_of_set_data_in_tuple = smashggapi.create_list_of_set_data_in_tuple(tournament_info, all_sets)
	sgg_tournament_data_tuple = smashggapi.create_sgg_tourney_data_in_tuple(tournament_info)
	boole = update_database_with_tournament_information(sgg_tournament_data_tuple)
	if boole:
		update_database_with_set_information(list_of_set_data_in_tuple)
		trueskillDictionary = create_trueskill_dictionary_for_tournament(entrant_id_to_player_id_dict)
		trueskillapi.update_trueskills(list_of_set_data_in_tuple, trueskillDictionary)
		update_player_database_with_new_trueskill(trueskillDictionary)
		print "Update complete!"
	else:
		print "Tournament already in the database."


def update_rankings_for_challonge_tournament(tourneyURL, subdomain=None):
	if subdomain:
		tourneyURL = subdomain + "-" + tourneyURL
	list_of_all_sets = challongeapi.get_all_the_sets(tourneyURL)
	challonge_player_dicts = challongeapi.challonge.participants.index(tourneyURL)
	list_of_player_tags = map(lambda dictionary: dictionary["name"], challonge_player_dicts)
	sponsors = ["Secret", "CLG", "TSM", "ePG", "UW", "WSU", "SU", "n3", "ESS", "WWU", "[62-Bit]", "62-bit", "62bit", "PHG", "CACAW", "GHQ", "URT"]
	loweredSponsors = map(lambda string: string.lower(), sponsors)
	no_bracket_tag_list = challongeapi.bracket_sponsor_remover(list_of_player_tags)
	stripped_sponsor_list = challongeapi.create_stripped_sponsor_list(no_bracket_tag_list, loweredSponsors)
	lowered_stripped_sponsor_list = map(lambda string: string.lower(), stripped_sponsor_list)
	db_tag_list = challongeapi.create_db_tag_list_for_comparison()
	dictionary_of_close_matches_from_tournament_and_database = challongeapi.fuzzy_string_match_ratio(lowered_stripped_sponsor_list, db_tag_list)
	final_tag_list = challongeapi.confirm_or_deny_existing_player(lowered_stripped_sponsor_list, dictionary_of_close_matches_from_tournament_and_database)
	shin_final_tag_list = challongeapi.check_for_alternate_tags(final_tag_list)
	entrant_id_to_player_id_dict = challongeapi.update_entrant_id_to_player_id_dict_and_player_database(list_of_player_tags, shin_final_tag_list, challonge_player_dicts)
	print entrant_id_to_player_id_dict
	finalized_sets_with_db_id_and_scores = challongeapi.finalize_sets_with_updated_winner_loser_id_and_score(entrant_id_to_player_id_dict, list_of_all_sets)
	list_of_set_tuples = challongeapi.create_list_of_set_data_in_tuple(finalized_sets_with_db_id_and_scores)
	challonge_tournament_data_tuple = challongeapi.create_challonge_tourney_data_in_tuple(tourneyURL)
	boole = update_database_with_tournament_information(challonge_tournament_data_tuple)
	if boole:
		update_database_with_set_information(list_of_set_tuples)
		trueskillDictionary = create_trueskill_dictionary_for_tournament(entrant_id_to_player_id_dict)
		trueskillapi.update_trueskills(list_of_set_tuples, trueskillDictionary)
		update_player_database_with_new_trueskill(trueskillDictionary)
		print "Update complete!"
	else:
		print "Tournament already in the database."




"""
#SGG Tournaments
update_rankings_for_smashgg_tournament("reign-2", "melee-singles")
"""
#update_rankings_for_challonge_tournament("oop0hkl8", "epeengaming")


def merge_players(real_tag, list_of_incorrect_tags):
	con = sqlite3.connect("ctest1smashggperfect.db")
	with con:
		cur = con.cursor()
		cur.execute("SELECT id FROM players WHERE tag=?", (real_tag,))
		correct_id = cur.fetchone()

		cur.execute("SELECT id FROM players WHERE tag in ('{}')"
			.format("', '".join(list_of_incorrect_tags)))
		print(correct_id)

		incorrect_tag_ids = ", ".join(map(lambda row: str(row[0]), cur.fetchall()))

		cur.execute("""
			UPDATE sets
			SET winner_id={}
			WHERE winner_id in ({})
			""".format(correct_id[0], incorrect_tag_ids))

		cur.execute("""
			UPDATE sets
			SET loser_id={}
			WHERE loser_id in ({})
			""".format(correct_id[0], incorrect_tag_ids))

		cur.execute("""
			DELETE FROM players
			WHERE id in ({})
			""".format(incorrect_tag_ids)
			)



def recalculate_all_trueskill_for_all_sets_in_db():
	con = sqlite3.connect("ctest1smashggperfect.db")
	with con:
		cur = con.cursor()
		cur.execute("SELECT id from players")
		db_ids = cur.fetchall()
		trueskillDictionary = dict(map(lambda db_id: (db_id[0], [trueskillapi.defaultRating.mu, trueskillapi.defaultRating.sigma]), db_ids))
		cur.execute("SELECT winner_id, loser_id, winner_score, loser_score FROM sets")
		sets = cur.fetchall()
		trueskillapi.update_trueskills(sets, trueskillDictionary)
        update_player_database_with_new_trueskill(trueskillDictionary)
        print "Trueskill recalculated!"



def merge_players(real_tag, list_of_incorrect_tags):
	con = sqlite3.connect("ctest1smashggperfect.db")
	with con:
		cur = con.cursor()
		cur.execute("SELECT id FROM players WHERE tag=?", (real_tag,))
		correct_id = cur.fetchone()

		cur.execute("SELECT id FROM players WHERE tag in ('{}')"
			.format("', '".join(list_of_incorrect_tags)))
		print(correct_id)

		incorrect_tag_ids = ", ".join(map(lambda row: str(row[0]), cur.fetchall()))

		cur.execute("""
			UPDATE sets
			SET winner_id={}
			WHERE winner_id in ({})
			""".format(correct_id[0], incorrect_tag_ids))

		cur.execute("""
			UPDATE sets
			SET loser_id={}
			WHERE loser_id in ({})
			""".format(correct_id[0], incorrect_tag_ids))

		cur.execute("""
			DELETE FROM players
			WHERE id in ({})
			""".format(incorrect_tag_ids)
			)

	recalculate_all_trueskill_for_all_sets_in_db()





'''
select tournaments.name, tournaments.url, winners.tag, losers.tag, sets.* from sets
inner join players AS winners on sets.winner_id = winners.id
inner join players AS losers on sets.loser_id = losers.id
inner join tournaments on sets.db_tournament_id = tournaments.id
where (winners.tag = 'dz' and losers.tag in ('rustin', 'chevy'))
or (losers.tag = 'dz' and winners.tag in ('


select display_tag, ROUND((trueskill_mu - 3*trueskill_sigma),3) as weighted_trueskill from players
 WHERE players.location = 'WA'
ORDER BY weighted_trueskill DESC;
'''
