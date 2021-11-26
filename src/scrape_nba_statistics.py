import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from sklearn.preprocessing import Normalizer


class Scraper():

    @staticmethod
    def build_team_urls(url):
        """
        get the url of each team from https://www.espn.com/nba/stats/team/

        :param url: str: url of the team site
        :return: dict: team name and team url pair
        """
        # Open the espn teams webpage and extract the names of each roster available.
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        table = soup.find("table", class_="Table--fixed-left")
        team_links = table.find_all("a", class_="AnchorLink")
        # Using the names of the rosters, create the urls of each roster
        roster_urls = []
        for link in team_links:
            elements = link.get("href").split("/")
            team_name = elements[-1]
            roster_urls.append((team_name, 'https://www.espn.com/nba/team/roster/_/name/' + elements[-2] + '/' + elements[-1]))
        return dict(roster_urls)

    @staticmethod
    def get_player_info(url):
        """
        get the player name, id and salary from roster page

        :param roster_url: str: url of team roster page
        :return: dict: player name as key, player name, id and salary as value
        """
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        table = soup.find("tbody")
        player_elements = table.find_all("td", class_="Table__TD")
        # get the salary
        salary = []
        for element in player_elements[7::8]:
            salary.append(element.find("div").text.strip())

        play_info = dict()
        for idx, element in enumerate(player_elements[1::8]):
            link = element.find("a")
            player_id = re.findall(r'\d+', link.get("href"))[0]
            play_info[link.text.strip()] = {"id": player_id, "name": link.text.strip(), "salary": salary[idx]}

        return play_info

    @staticmethod
    def get_player_stats(url):
        """
        get stats of a player

        :param url: str: url of player stats page
        :return: list: the points scored, assists, rebounds, and time played
        """
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        table = soup.find_all("tbody")[1].find_all("tr")[-1]
        stats = [element.find("span").text.strip() for element in table]
        return list(map(float, [stats[2], stats[11], stats[12], stats[-1]]))

    def _scrape_data(self, team_url):
        """
        scrape data from team site, get player stats

        :param team_url: str: team site url
        """
        # scrape player information from rosters
        rosters = self.build_team_urls(team_url)
        all_players = dict()
        for team in rosters.keys():
            print("Gathering player info for team: " + team)
            all_players[team] = self.get_player_info(rosters[team])

        # loop through each team, create a pandas DataFrame, and append
        all_players_df = pd.DataFrame()
        for team in all_players.keys():
            team_df = pd.DataFrame.from_dict(all_players[team], orient = "index")
            team_df['team'] = team
            all_players_df = all_players_df.append(team_df)

        # scrape career statistics
        print ("Gathering stats on all players:")
        career_stats_df = pd.DataFrame(columns = ["MIN", "REB", "AST", "PTS"])
        for idx, row in all_players_df.iterrows():
            print("Gathering player info for: " + idx)
            url = "https://www.espn.com/nba/player/stats/_/id/" + str(row['id']) + "/type/nba/seasontype/3"
            try:
                career_info = self.get_player_stats(url)
                career_stats_df = career_stats_df.append(pd.Series(career_info, index = career_stats_df.columns, name=idx))
            except:
                print(idx + " has no info, " + url)

        # join and clean the data
        self.df = all_players_df.join(career_stats_df)

    def _clean_up(self, df):
        # change salary type to int
        df.loc[:, 'salary'] = df['salary'].replace("--", pd.NA)
        df.loc[:, 'salary'] = [int(re.sub(r'[^\d.]+', '', s)) if isinstance(s, str) else s for s in df['salary'].values]
        # drop na
        df = df.dropna(subset=["MIN", "PTS", "REB", "AST"])

        return df

    def _create_metric(self):
        columns = ["MIN", "PTS", "REB", "AST"]
        # normalize
        normalized_df = Normalizer().fit_transform(self.df.loc[:, columns])
        normalized_df = pd.DataFrame(normalized_df, columns=columns)
        # get scale
        scale = (normalized_df.max() - normalized_df.min())/100

        metric = (normalized_df["PTS"] + scale["PTS"] ) * (normalized_df["MIN"] + scale["MIN"]) * (normalized_df["REB"] + scale["REB"]) * (normalized_df["AST"] + scale["AST"])
        self.df["metric"] = metric.values * 10000

    def save(self):
        self.df.to_json("NBA_player_info.json", orient="records")

    def read(self):
        self.df = pd.read_json("NBA_player_info.json", orient="records")

    def __call__(self, team_url=None):
        if team_url:
            self._scrape_data(team_url)
            self.df = self._clean_up(self.df)
            self._create_metric()
            self.save()
        else:
            self.read()
            self.df = self._clean_up(self.df)
            self._create_metric()
            self.save()

        return self.df
