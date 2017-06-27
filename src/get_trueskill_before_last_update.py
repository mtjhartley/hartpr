"""
Trueskill over time idea:

Pull all sets except from those in a certain tournament(s)
Recalculate trueskill (dependent on literally everyone...)



"""
import datetime
import database
import trueskillapi

start = datetime.datetime.now()

def get_last_tournament_id():
	query = database.queryMany("""SELECT id FROM tournaments ORDER BY calendar_date DESC LIMIT 5;""")
	return (query[0][0], query[1][0], query[2][0], query[3][0], query[4][0],)
print get_last_tournament_id()


def recalculate_all_trueskill_for_all_sets_in_db():
	last_tournament_id = get_last_tournament_id()
	db_ids = database.queryMany("SELECT id FROM players")
	print "all ids obtained"
	trueskillDictionary = dict(map(lambda db_id: (db_id[0], [trueskillapi.defaultRating.mu, trueskillapi.defaultRating.sigma]), db_ids))
	sets = database.queryMany("SELECT winner_id, loser_id, winner_score, loser_score FROM sets WHERE db_tournament_id NOT IN %s", (last_tournament_id,))
	#print len(sets)
	trueskillapi.update_trueskills(sets, trueskillDictionary)
	print trueskillDictionary[13][0] - trueskillDictionary[13][1] * 3 

	trueskillDictionary = dict(map(lambda db_id: (db_id[0], [trueskillapi.defaultRating.mu, trueskillapi.defaultRating.sigma]), db_ids))
	sets = database.queryMany("SELECT winner_id, loser_id, winner_score, loser_score FROM sets WHERE db_tournament_id NOT IN %s", (last_tournament_id[1:],))
	#print len(sets)
	trueskillapi.update_trueskills(sets, trueskillDictionary)
	print trueskillDictionary[13][0] - trueskillDictionary[13][1] * 3 

	trueskillDictionary = dict(map(lambda db_id: (db_id[0], [trueskillapi.defaultRating.mu, trueskillapi.defaultRating.sigma]), db_ids))
	sets = database.queryMany("SELECT winner_id, loser_id, winner_score, loser_score FROM sets WHERE db_tournament_id NOT IN %s", (last_tournament_id[2:],))
	#print len(sets)
	trueskillapi.update_trueskills(sets, trueskillDictionary)
	print trueskillDictionary[13][0] - trueskillDictionary[13][1] * 3 

	trueskillDictionary = dict(map(lambda db_id: (db_id[0], [trueskillapi.defaultRating.mu, trueskillapi.defaultRating.sigma]), db_ids))
	sets = database.queryMany("SELECT winner_id, loser_id, winner_score, loser_score FROM sets WHERE db_tournament_id NOT IN %s", (last_tournament_id[3:],))
	#print len(sets)
	trueskillapi.update_trueskills(sets, trueskillDictionary)
	print trueskillDictionary[13][0] - trueskillDictionary[13][1] * 3 

	trueskillDictionary = dict(map(lambda db_id: (db_id[0], [trueskillapi.defaultRating.mu, trueskillapi.defaultRating.sigma]), db_ids))
	sets = database.queryMany("SELECT winner_id, loser_id, winner_score, loser_score FROM sets WHERE db_tournament_id NOT IN %s", (last_tournament_id[4:],))
	#print len(sets)
	trueskillapi.update_trueskills(sets, trueskillDictionary)
	print trueskillDictionary[13][0] - trueskillDictionary[13][1] * 3 


	trueskillDictionary = dict(map(lambda db_id: (db_id[0], [trueskillapi.defaultRating.mu, trueskillapi.defaultRating.sigma]), db_ids))
	sets = database.queryMany("SELECT winner_id, loser_id, winner_score, loser_score FROM sets")
	#print len(sets)
	trueskillapi.update_trueskills(sets, trueskillDictionary)
	print trueskillDictionary[13][0] - trueskillDictionary[13][1] * 3 
	#update_player_database_with_new_trueskill(trueskillDictionary)
	print "Trueskill recalculated!"

recalculate_all_trueskill_for_all_sets_in_db()

end = datetime.datetime.now()

print end - start