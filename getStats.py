from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
import pandas as pd

# Function to get a specific player's ID
def get_player_id(player_name):
    for player in all_players:
        if player['full_name'].lower() == player_name.lower():
            return player['id']

# Function to get game log data for a player
def get_game_log(player_id, season='2022'):
    for retry in range(10):  # Retrying up to 10 times
        try:
            game_log = playergamelog.PlayerGameLog(player_id=player_id, season=season)
            return game_log.get_data_frames()[0]
        except (requests.exceptions.ConnectionError, requests.exceptions.NameResolutionError):
            print(f"Failed to fetch data for player {player_id}. Retrying ({retry+1}/10)...")
            time.sleep(5)  # Wait for 5 seconds before retrying
    print(f"Failed to fetch data for player {player_id} after 10 retries.")
    return None  # Return None if all retries fail

# Function to calculate per-game stats
def calculate_per_game_stats(df):
    total_games = len(df)
    if total_games == 0:
        return None
    stats = {
        "ppg": df['PTS'].sum() / total_games,
        "rpg": df['REB'].sum() / total_games,
        "apg": df['AST'].sum() / total_games,
        "spg": df['STL'].sum() / total_games,
        "bpg": df['BLK'].sum() / total_games,
        "fgm": df['FGM'].sum() / total_games,
        "fga": df['FGA'].sum() / total_games,
        "TO": df['TOV'].sum() / total_games,
        "FG3M": df['FG3M'].sum() / total_games,
        "FG3A": df['FG3A'].sum() / total_games,
        "FTM": df['FTM'].sum() / total_games,
        "FTA": df['FTA'].sum() / total_games
    }
    # Calculate field goal percentage
    if stats["fga"] == 0:
        stats["fg%"] = 0
    else:
        stats["fg%"] = (stats["fgm"] / stats["fga"]) * 100

    if stats["FG3A"] == 0:
        stats["3PT%"] = 0
    else:
        stats["3PT%"] = (stats["FG3M"] / stats["FG3A"]) * 100
    
    if stats["FTA"] == 0:
        stats["ft%"] = 0
    else:
        stats["ft%"] = (stats["FTM"] / stats["FTA"]) * 100

    return stats

# Function to populate player_stats dictionary
def populate_player_stats(player_name, season):
    print("Current player:" + player_name)
    player_id = get_player_id(player_name)
    if not player_id:
        return None

    game_log_df = get_game_log(player_id, season)
    #print(game_log_df.columns)

    stats = calculate_per_game_stats(game_log_df)
    
    if not stats:
        return None

    player_stats = {
        "Name": player_name,
        "ppg": stats['ppg'],
        "rpg": stats['rpg'],
        "apg": stats['apg'],
        "spg": stats['spg'],
        "bpg": stats['bpg'],
        "fgm": stats['fgm'],
        "fga": stats['fga'],
        "fg%": stats['fg%'],
        "TO": stats['TO'],
        "FG3M": stats["FG3M"],
        "FG3A": stats["FG3A"],
        "FTM": stats["FTM"],
        "FTA": stats["FTA"],
        "ft%": stats["ft%"],
        "3PT%": stats["3PT%"],
        "egp": 75  # Example value
    }
    return player_stats

# Fetch all NBA players
all_players = players.get_players()

# Function to calculate average minutes per game
def calculate_avg_mpg(df):
    total_games = len(df)
    if total_games == 0:
        return 0
    avg_mpg = df['MIN'].sum() / total_games
    return avg_mpg

# Main program
if __name__ == "__main__":
    # Specific NBA season
    season = '2022'

    # Create an empty DataFrame to hold player statistics
    stats_df = pd.DataFrame()

    # Fetch stats for each player and append to DataFrame
    for player in all_players:
        if player['is_active'] == 'False':
            continue
        player_name = player['full_name']
        player_id = get_player_id(player_name)
        
        if not player_id:
            continue

        game_log_df = get_game_log(player_id, season)
        if game_log_df is None:
            continue
        avg_mpg = calculate_avg_mpg(game_log_df)

        # Check if average MPG is at least 20
        if avg_mpg < 20:
            continue

        stats = populate_player_stats(player_name, season)
        if stats:
            stats_df = stats_df._append(stats, ignore_index=True)

    # Save DataFrame to CSV file
    stats_df.to_csv("all_player_stats.csv", index=False)

