from typing import List, Tuple
from riotapi import MatchListApi, MatchApi, SummonerApi, RitoPlsError
from riotdata import ChampionData
from rediscache import RedisCache
from utils import map_key

class GameAnalyzer:

    def __init__(self, summoner_name):
        self.summoner_name = summoner_name

    def analyze_last_game(self):
        match_data = self._get_last_game()
        analyzer = PlayerAnalyzer(self.summoner_name, match_data)
        return analyzer.analyze()

    def _get_last_game(self):
        # Initialize apis
        champions = ChampionData()

        summoner_api = SummonerApi()
        match_api = MatchApi()

        summoners = RedisCache('summoners_', summoner_api.get)
        matches = RedisCache('matches_', match_api.get)

        # get account id
        summmoner_data = summoners[self.summoner_name]
        account_id = summmoner_data['accountId']

        # get last games 
        match_list = MatchListApi().get(account_id)['matches']
        game_ids = [match['gameId'] for match in match_list]


        def champ_mapper(i):
            try:
                return champions[i]
            except ValueError:
                return i

        for game_id in game_ids:
            try:
                match = matches[game_id]
                map_key(match, 'championId', champ_mapper)
                return match                
            except RitoPlsError:
                continue
        raise RitoPlsError(f'No games for {self.summoner_name} found')

   
class Player:
    dog_champs = {'Evelynn', 'Talon', 'Master Yi', 'Twitch'}

    def __init__(self, source: dict):
        self.pid = source['participantId']
        self.kills = source['stats']['kills']
        self.assists = source['stats']['assists']
        self.deaths = source['stats']['deaths']
        self.win = source['stats']['win']
        self.largest_multikill = source['stats']['largestMultiKill']
        self.team = source['teamId']
        self.gold = source['stats']['goldEarned']
        self.role = source['timeline']['role']
        self.summoner_name = source['summoner_name']
        
        try:
            self.champion = source['championId']['name']
            self.champion_tags = set(source['championId']['tags'])
        except (KeyError, TypeError):
            self.champion = 'Unknown'
            self.champion_tags = set()
    
    def __str__(self):
        return self.champion

    def is_dog_champ(self):
        return 'Assassin' in self.champion_tags or self.champion in self.dog_champs

    def is_support(self):
        return 'Support' in self.champion_tags

    def is_troll_support(self):
        return self.role == 'SUPPORT' and not self.is_support()

    @property
    def kd(self):
        return self.kills /(self.deaths + 0.00000001)

    @property
    def died_alot(self):
        return self.kd < 0.8 and self.deaths > 7

    @property
    def inted(self):
        return self.kd < 0.15 and self.deaths > 7

    @property
    def was_fed(self):
        return self.kd > 2 and self.kills > 5

class PlayerAnalyzer:

    def __init__(self, summoner_name, game):
        self.game = game
        self.move_summoner_names(self.game)
        self.players = self.parse_players(self.game)
        self.summoner_name = summoner_name
        self.player = self.get_player(summoner_name)
        self.home_team, self.enemy_team = self.divide_to_teams()
        self.bad_game_strs = [f'{self.summoner_name} had a rough game:']
        self.neutral_game_strs = [f'{self.summoner_name} had ok game:']
        self.good_game = [f'{self.summoner_name} had ok game:']

    @staticmethod
    def move_summoner_names(game: dict) -> None:
        name_id_map = {}
        for player in game['participantIdentities']:
            pid = player['participantId']
            name = player['player']['summonerName']
            name_id_map[pid] = name

        for participant in game['participants']:
            participant['summoner_name'] = name_id_map[participant['participantId']]

    def parse_players(self, game: dict) -> List[Player]:
        return [Player(participant) for participant in game['participants']]


    def get_player(self, name) -> Player:
        for player in self.players:
            if player.summoner_name == name:
                return player
        raise ValueError(f"{name} not found in summoner names")

    def divide_to_teams(self) -> Tuple[List[Player], List[Player]]:
        home_team = []
        enemy_team = []
        for player in self.players:
            team_list = home_team if player.team == self.player.team else enemy_team
            team_list.append(player)
        return home_team, enemy_team

    def analyze(self):
        score = 0
        positives = []
        negatives = []

        # mixed influence stats
        if self.player.win:
            score += 3
            positives.append('Player Won the game.')
        else:
            score -= 3
            positives.append('Player Lost the game.')

        # positive influence
        
        if self.player.largest_multikill > 2:
            score += 1
            positives.append(f'Player Had largest multikill of {self.player.largest_multikill}')
        
        if self.player.was_fed:
            score +=2
            positives.append(('Player Was fed with stats ' 
                              '{self.player.kills}/{self.player.deaths}/{self.player.assists}'))

        # negative influence
        if self.player.died_alot:
            score -= 2
            negatives.append(f'Player died {self.player.deaths} times')

        dog_champs = [player for player in self.enemy_team if player.is_dog_champ]
        if dog_champs:
            score -= len(dog_champs)
            champ_names = [player.champion for player in dog_champs]
            negatives.append('Enemies had nasty champs.({})'.format(','.join(champ_names)))
        
        for dog in dog_champs:
            if dog.was_fed:
                score -=2
                negatives.append(f'Enemies had fed {dog}')

        troll_supports = [player for player in self.home_team if player.is_troll_support]
        if troll_supports:
            score -= 2
            support_names = [player.champion for player in troll_supports]
            negatives.append("Players team had troll support(s): {}".format(', '.join(support_names)))

        if score < 0:
            return negatives
        return positives

if __name__ == '__main__':
    analyzer = GameAnalyzer('Hobiiri')
    print(analyzer.analyze_last_game())
