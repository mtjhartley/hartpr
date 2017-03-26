import psycopg2
import smashggapi
import trueskillapi
import pysmash
import challongeapi
import os
import urlparse

urlparse.uses_netloc.append("postgres")
url = None
if os.environ.get("DATABASE_URL", None):
	url = urlparse.urlparse(os.environ["DATABASE_URL"])

db = None
def get_db():
	global db
	if db == None:
		if url:
			db = psycopg2.connect(
			    database=url.path[1:],
			    user=url.username,
			    password=url.password,
			    host=url.hostname,
			    port=url.port
			)
		else:
			db = psycopg2.connect("dbname=hartprdb user=postgres password=password") #../db/finaltestdb.db when need to update...
	return db

def queryMany(q, args=None):
	db = get_db()
	cur = db.cursor()

	if (args == None):
		cur.execute(q.replace("?", "%s"))
	else:
		cur.execute(q.replace("?", "%s"), args)

	db.commit()
	return cur.fetchall()

def queryOne(q, args=None):
	db = get_db()
	cur = db.cursor()

	if (args == None):
		cur.execute(q.replace("?", "%s"))
	else:
		cur.execute(q.replace("?", "%s"), args)

	db.commit()
	return cur.fetchone()

def queryInsert(q, args=None):
	db = get_db()
	cur = db.cursor()

	if (args == None):
		cur.execute(q.replace("?", "%s"))
	else:
		cur.execute(q.replace("?", "%s"), args)

	db.commit()
	return cur.lastrowid

def get_all_sponsors():
	sponsors = []
	rows = queryMany("""SELECT sponsor from sponsors""")
	for row in rows:
		sponsors.append(row[0])
	return sponsors

def update_database_with_tournament_information(tourney_data_in_tuple):
	try:	
		queryOne("INSERT INTO tournaments (name, url, calendar_date, unique_tournament_id, website, subdomain) VALUES(?,?,?,?,?,?);", tourney_data_in_tuple)
		return True
	except sqlite3.IntegrityError:
		print "Did not add duplicate tournament to database."
		return False

def update_database_with_set_information(list_of_set_data_in_tuples):
	unique_tournament_id = list_of_set_data_in_tuples[0][6]
	try:
		rows = queryOne("SELECT id FROM tournaments WHERE unique_tournament_id=?", (unique_tournament_id,))
		db_tourney_id = rows[0] 
		new_list_of_set_data_in_tuples = []
		#set_tuple = (database_winner_id, database_loser_id, winner_score, loser_score, set_id, bracket_id, unique_tournament_id, phase) unique is index 6
		for tuple_data in list_of_set_data_in_tuples:
			new_tuple = (tuple_data[0], tuple_data[1], tuple_data[2], tuple_data[3], tuple_data[4], tuple_data[5], tuple_data[7])
			new_tuple = new_tuple + (db_tourney_id,)
			new_list_of_set_data_in_tuples.append(new_tuple)
		queryMany("INSERT INTO sets(winner_id, loser_id, winner_score, loser_score, set_id, bracket_id, phase, db_tournament_id) VALUES (?,?,?,?,?,?,?,?)", new_list_of_set_data_in_tuples)
		print "Sets were successfully added to the database"
	except sqlite3.IntegrityError:
		print "Duplicate sets were not added to the database."

def create_trueskill_dictionary_for_tournament(entrant_to_player_dict):
	trueskillDictionary = {}
	for player in entrant_to_player_dict:
		db_id = entrant_to_player_dict[player]
		db_id_tuple = (db_id,)
		rows = queryOne("SELECT trueskill_mu, trueskill_sigma FROM players WHERE id=?", db_id_tuple)
		trueskill_list = []
		for row in rows:
			trueskill_list.append(row)
		trueskillDictionary[db_id] = trueskill_list
	return trueskillDictionary

def update_player_database_with_new_trueskill(trueskillDictionary):
	list_of_db_player_ids = trueskillDictionary.keys()
	for db_player_id in list_of_db_player_ids:
		new_trueskill_list = trueskillDictionary[db_player_id]
		new_trueskill_list.append(db_player_id)
		new_trueskill_mu = new_trueskill_list[0]
		new_trueskill_sigma = new_trueskill_list[1]
		update_tuple = (new_trueskill_list[0], new_trueskill_list[1], db_player_id)
		queryOne("UPDATE players SET trueskill_mu=?, trueskill_sigma=? WHERE id=?", update_tuple)


#new main.py ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def update_rankings_for_smashgg_tournament(tourneyName, bracketName):
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
	sponsors = get_all_sponsors()
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
	challonge_tournament_data_tuple = challongeapi.create_challonge_tourney_data_in_tuple(tourneyURL, subdomain)
	boole = update_database_with_tournament_information(challonge_tournament_data_tuple)
	if boole:
		update_database_with_set_information(list_of_set_tuples)
		trueskillDictionary = create_trueskill_dictionary_for_tournament(entrant_id_to_player_id_dict)
		trueskillapi.update_trueskills(list_of_set_tuples, trueskillDictionary)
		update_player_database_with_new_trueskill(trueskillDictionary)
		print "Update complete!"
	else:
		print "Tournament already in the database."

def recalculate_all_trueskill_for_all_sets_in_db():
	db_ids = queryMany("SELECT id FROM players")
	trueskillDictionary = dict(map(lambda db_id: (db_id[0], [trueskillapi.defaultRating.mu, trueskillapi.defaultRating.sigma]), db_ids))
	sets = queryMany("SELECT winner_id, loser_id, winner_score, loser_score FROM sets")
	trueskillapi.update_trueskills(sets, trueskillDictionary)
	update_player_database_with_new_trueskill(trueskillDictionary)
	print "Trueskill recalculated!"

def merge_players(real_tag, list_of_incorrect_tags):

	correct_id = queryOne("SELECT id FROM players WHERE tag=?", (real_tag,))
	ids = queryMany("SELECT id FROM players WHERE tag in ('{}')"
		.format("', '".join(list_of_incorrect_tags)))
	incorrect_tag_ids = ", ".join(map(lambda row: str(row[0]), ids))

	queryMany("""
		UPDATE sets
		SET winner_id={}
		WHERE winner_id in ({})
		""".format(correct_id[0], incorrect_tag_ids))

	queryMany("""
		UPDATE sets
		SET loser_id={}
		WHERE loser_id in ({})
		""".format(correct_id[0], incorrect_tag_ids))

	queryMany("""
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

