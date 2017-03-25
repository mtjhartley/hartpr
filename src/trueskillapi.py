import trueskill

global_environment = trueskill.TrueSkill(draw_probability = 0)

defaultRating = trueskill.Rating(25)

"""This currently takes the dictionary created by 
smashggapi.create_trueskill_dict for tournament (which should be global),
In that dictionary, the database is called and a dictionary is created where 
the trueskill mu and sigma are given in a length 2 list. 

This function creates a trueskill object for every player based on those values, 
and puts them through the 1v1 for every set played in the tournament, requires 
a flat set list.

Lastly, it takes the trueskill object and separates the new mu and sigma into
numbers in a list like the original input. Not sure if we should return the dictionary
or just leave it "updated, guess it depends on how we write the update database code."
"""

#definitely just do this with the set tuple lool

def update_trueskills(finalized_set_tuples, trueskillDictionary):
	for player in trueskillDictionary:
		old_trueskill_mu = trueskillDictionary[player][0]
		old_trueskill_sigma = trueskillDictionary[player][1]
		old_trueskill_object = trueskill.Rating(old_trueskill_mu, old_trueskill_sigma) 
		trueskillDictionary[player] = old_trueskill_object
	#don't do this if the score is -1 for either player
	#how can we handle unfinished brackets? no winner_loser_id...
	for finalized_set_tuple in finalized_set_tuples: 

		try:
			if not (finalized_set_tuple[2] == -1 or finalized_set_tuple[3] == -1):

				winner = finalized_set_tuple[0]
				loser = finalized_set_tuple[1]
				winner_old_trueskill = trueskillDictionary[winner]
				loser_old_trueskill = trueskillDictionary[loser] 

				winner_new_trueskill, loser_new_trueskill = trueskill.rate_1vs1(winner_old_trueskill, loser_old_trueskill)

				trueskillDictionary[winner] = winner_new_trueskill
				trueskillDictionary[loser] = loser_new_trueskill
		except KeyError:
			pass


	for player in trueskillDictionary:
		new_trueskill_list = []
		new_trueskill_mu = trueskillDictionary[player].mu 
		new_trueskill_sigma = trueskillDictionary[player].sigma
		new_trueskill_list.append(new_trueskill_mu)
		new_trueskill_list.append(new_trueskill_sigma)

		trueskillDictionary[player] = new_trueskill_list



#update this to work not with tags, but with database_winner_id and database_loser_id

#then after making the dictionary i figure we query the db and alter the table columns 
#so people get the updated trueskills but not too clear on that.

