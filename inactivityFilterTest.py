from flask import Flask, render_template, request, redirect, url_for, request, session, abort, Response, flash
import flask_login
import src.database as db
from time import time
import datetime
import os

"""
Go through every player in the database where state = WA, ordered by trueskill descending. 
For each player in the database, get their most recent set 
(query sets with their id, order by calendar-date descending)
Get the date from that set
Is the date within 30 days of the current day?
If so, add that player id back into a new list
If it ain't dont
Then I have a list of active players...
Query db one last time with this list?

"""

start2 = datetime.datetime.now()
unfilteredPlayerRows = db.queryMany("""SELECT *,  Round((trueskill_mu-3*trueskill_sigma),3) AS weighted_trueskill
				FROM players 
				WHERE players.location = 'WA' 
				ORDER BY weighted_trueskill desc;
				""")

print unfilteredPlayerRows
lap1 = datetime.datetime.now()

#does this query 849 times lol...
playerRecencyList = []
for player in unfilteredPlayerRows:
	playerId = (player[0], player[0])
	lastPlayedDate = db.queryMany("""SELECT tournaments.name, tournaments.id, tournaments.calendar_date, winners.id, losers.id, winners.tag, losers.tag, winners.display_tag, losers.display_tag, sets.* FROM sets
			inner join players AS winners on sets.winner_id = winners.id
			inner join players AS losers on sets.loser_id = losers.id
			inner join tournaments on sets.db_tournament_id = tournaments.id
			WHERE (winners.id=%s or losers.id=%s)
			AND (loser_score IS NULL OR loser_score != -1)
			ORDER BY calendar_date DESC
			LIMIT 1;
			""", playerId)
	try:
		playerRecencyList.append((player, lastPlayedDate[0][2]))
	except IndexError: #they were never active...
		pass

print playerRecencyList
lap2 = datetime.datetime.now()

def days_difference(now, then):
	delta = now - then
	return delta.days + delta.seconds + delta.microseconds/1000000

activePlayers = []
for player in playerRecencyList:
	now = datetime.datetime.now().date()
	lastPlayedDate = datetime.datetime.strptime(player[1], '%Y-%m-%d').date()
	daysSinceLastTournament = days_difference(now, lastPlayedDate)
	print "The player has not been active for this many days:", daysSinceLastTournament
	if daysSinceLastTournament < 45:  #days
		activePlayers.append(player[0])


end2 = datetime.datetime.now()
print end2-start2

print "first query", lap1 - start2 #instant
print "second query batch", lap2-lap1 #7 seconds lol
print len(activePlayers)
print len(unfilteredPlayerRows)

#idea...we can get the last active date of every player
#add this to a column in the player db
#display them based on this...1 query per player!
#when we add a new torurnament, everyone who went gets updated to the tourney date
#this way we dont have to query activity when we query everyone
#cons - can only use most recent (1) tournament as an activity requirement.






