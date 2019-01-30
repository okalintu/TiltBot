import logging
import random
import pytz
from datetime import datetime
from typing import List, Tuple
from riotapi import MatchListApi, MatchApi, SummonerApi, RitoPlsError
from riotdata import ChampionData
from rediscache import RedisCache
from utils import map_key, LogMixin

class GameAnalyzer(LogMixin):

    def __init__(self, summoner_name):
        self.summoner_name = summoner_name

    def analyze_last_game(self, raw=False):
        match_data = self._get_last_game()
        analyzer = PlayerAnalyzer(self.summoner_name, match_data)
        return analyzer.analyze(raw)

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

        for game_id in game_ids:
            try:
                match = matches[game_id]
                map_key(match, 'championId', lambda i: champions.get(i, i))
                return match                
            except RitoPlsError:
                continue
        raise RitoPlsError(f'No games for {self.summoner_name} found')

class Player(LogMixin):
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
        self.lane = source['timeline']['lane']
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
        if self.champion == 'Unknown':
            return False
        is_troll = self.role == 'DUO_SUPPORT' and not self.is_support()
        return is_troll

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


class PlayerAnalyzer(LogMixin):
    ok_threshold = -10
    good_threshold = 50

    def __init__(self, summoner_name, game):
        self.game = game
        self.gameStarted = datetime.fromtimestamp(game['gameCreation']/1000).replace(tzinfo=pytz.UTC)
        self.gameStarted_str = self.gameStarted.strftime('%Y-%m-%d %H:%M:%S UTC') 
        self.move_summoner_names(self.game)
        self.players = self.parse_players(self.game)
        self.summoner_name = summoner_name
        self.player = self.get_player(summoner_name)
        self.home_team, self.enemy_team = self.divide_to_teams()
        self.bad_game_strs = [f'{self.summoner_name} had a rough last game:']
        self.neutral_game_strs = [f'{self.summoner_name} had ok last game:']
        self.good_game_strs = [f'{self.summoner_name} had a good last game:']

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

    def analyze(self, raw=False):
        score = 0
        positives = []
        negatives = []

        # mixed influence stats
        if self.player.win:
            score += 30
            positives.append('Player Won the game.')
        else:
            score -= 30
            negatives.append('Player Lost the game.')

        # positive influence
        
        if self.player.largest_multikill > 2:
            score += self.player.largest_multikill*9
            positives.append(f'Player Had largest multikill of {self.player.largest_multikill}')
        
        if self.player.was_fed:
            score -= -1**self.player.win * 19
            positives.append(f'Player Was fed with stats {self.player.kills}/{self.player.deaths}/{self.player.assists}')

        # negative influence
        if self.player.died_alot:
            score -= 22
            negatives.append(f'Player died {self.player.deaths} times')

        dog_champs = [player for player in self.enemy_team if player.is_dog_champ()]
        if dog_champs:
            score -= len(dog_champs)*11
            champ_names = [player.champion for player in dog_champs]
            negatives.append('Enemies had nasty champs.({})'.format(','.join(champ_names)))
        
        for dog in dog_champs:
            if dog.was_fed:
                score -=21
                negatives.append(f'Enemies had fed {dog}')

        troll_supports = [player for player in self.home_team if player.is_troll_support()]
        if troll_supports:
            score -= 23
            support_names = [player.champion for player in troll_supports]
            negatives.append("Players team had troll support(s): {}".format(', '.join(support_names)))

        inting_teammates = []
        for player in self.home_team:
            if player.inted and not player == self.player:
                inting_teammates.append(player)

        for player in inting_teammates:
            score -= 24
            negatives.append('Player had inting {}({}/{}/{}) on their team'.format(
                player.champion,
                player.kills,
                player.deaths,
                player.assists))

        # non text factors
        score += 3*self.player.kills
        score += 1*self.player.assists
        score -= 4*self.player.deaths

        temp = self._calculate_temperature(score)
        if raw:
            stats = f"{self.player.kills}/{self.player.deaths}/{self.player.assists}"
            return (temp, stats, negatives, positives)
        if score < self.ok_threshold:
            return self._format_response(random.choice(self.bad_game_strs), temp, negatives)
        if score < self.good_threshold:
            return self._format_response(random.choice(self.neutral_game_strs), temp, negatives + positives)
        return self._format_response(random.choice(self.good_game_strs), temp, positives)


    def _format_response(self, header, temp, bulletpoints):
        tag = "```"
        bullet_str = ''
        for bp in bulletpoints:
            bullet_str+= f'    - {bp}\n'
        return f'{tag}markdown\n{header}\nTemperature: {temp}°C\nPlayed:{self.gameStarted_str}\n{bullet_str}{tag}'

    @staticmethod
    def _calculate_temperature(score: int)-> int:
        return int(10 + (max(0, 5 - score/10))**2)

if __name__ == '__main__':
    FORMAT = '%(asctime)-15s %(filename)15s:%(lineno)3d %(levelname)-8s %(message)s'
    logging.basicConfig(format=FORMAT)
    logger = logging.getLogger('TiltBot')
    logger.setLevel(logging.DEBUG)
    analyzer = GameAnalyzer('foobar')
    logger.debug(analyzer.analyze_last_game())
