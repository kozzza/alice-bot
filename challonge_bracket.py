from decouple import config
from datetime import datetime
import shortuuid
import challonge

class ChallongeTourney():
	
	def __init__(self, participants, tournament_name, game, url=shortuuid.uuid()[:8]):
		self.participants = participants
		self.tournament_name = tournament_name
		self.game = game
		self.url = url
		challonge.set_credentials(config('CHALLONGE_USERNAME'), config('CHALLONGE_API_KEY'))
	
	def create_tournament(self):
		try:
			challonge.tournaments.create(name=self.tournament_name, url=self.url, game_name=self.game, tournament_type='double elimination')
		except challonge.api.ChallongeException as e:
			self.url = shortuuid.uuid()[:8]
			self.create_tournament()
		
		for participant in self.participants:
			challonge.participants.create(tournament=self.url, name=participant)
		challonge.tournaments.start(self.url)

		return self.url

	def fetch_tournament(self):
		return challonge.tournaments.show(tournament=self.url)

	def fetch_matches(self, match_state='all'):
		matches = []
		for match in challonge.matches.index(tournament=self.url):
			if match["state"] == match_state:
				matches.append(match)
		return matches

	def fetch_participants(self):
		return challonge.participants.index(tournament=self.url)
	
	def set_match_score(self, match_id, winner, scores):
		scores_csv = ','.join(['-'.join([str(num) for num in score]) for score in scores])
		challonge.matches.update(tournament=self.url, match_id=match_id, winner_id=winner, scores_csv=scores_csv)

	def finalize(self):
		challonge.tournaments.finalize(tournament=self.url)

	def delete(self):
		challonge.tournaments.destroy(tournament=self.url)