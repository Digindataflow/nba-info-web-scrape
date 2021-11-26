from scrape_nba_statistics import Scraper
import argparse

URL = 'https://www.espn.com/nba/stats/team/_/season/2021/seasontype/3'

def main():
    parser = argparse.ArgumentParser(description='variables for the scraper.')
    parser.add_argument('--metric', metavar='M', choices=("metric", "salary"),
                        help='type of metric: metric or salary')
    parser.add_argument('--url', help='url of the team page')
    parser.add_argument('--update', action='store_true', default=False, help='scrape the data and save it')
    args = parser.parse_args()

    team_url = args.url if args.url else URL

    # update the data
    if args.update:
        all_stats_df = Scraper()(team_url)
    else:
        all_stats_df = Scraper()()

    print("------------------------------------")
    print("Top 10 players: ")
    if args.metric is None or args.metric == "metric":
        print(", ".join(list(all_stats_df.sort_values('metric', ascending=False).head(10)["name"])))
    elif args.metric == "salary":
        # clean up salary
        cleaned_df = all_stats_df.loc[~all_stats_df["salary"].isnull(), :]
        cleaned_df.loc[:, "salary"] = cleaned_df["salary"].astype(float)
        print(", ".join(list(cleaned_df.sort_values('salary', ascending=False).head(10)["name"])))
    else:
        raise ValueError("invalid metric")


if __name__ == "__main__":
    main()