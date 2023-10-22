import pandas as pd
import itertools
from fuzzywuzzy import process


# Function to aggregate team statistics
def aggregate_team_stats(team, df):
    stats = {
        'fgm': 0, 'fga': 0, 'FTM': 0, 'FTA': 0,
        'FG3M': 0, 'FG3A': 0, 'TO': 0, 'rpg': 0,
        'apg': 0, 'spg': 0, 'bpg': 0, 'ppg': 0, 'egp':0
    }
    weighted_stats = {
        'ppg': 0, 'rpg': 0, 'apg': 0, 'spg': 0,
        'bpg': 0, 'TO': 0
    }
    # Define multipliers
    multipliers = {
        'ppg': 1, 'rpg': 1, 'apg': 2, 'spg': 3,
        'bpg': 3, 'TO': -2
    }

    for player in team:
        player_stats = df[df['Name'] == player].iloc[0]
        for key in stats.keys():
            stats[key] += player_stats[key]
        for key in weighted_stats.keys():
            weighted_stats[key] += (player_stats[key] * player_stats['egp']) * multipliers[key]
    
    num_players = len(team)
    if num_players > 0:
        for key in weighted_stats.keys():
            weighted_stats[key] /= num_players

    # Calculate percentages
    stats['fg%'] = (stats['fgm'] / stats['fga']) * 100 if stats['fga'] != 0 else 0
    stats['ft%'] = (stats['FTM'] / stats['FTA']) * 100 if stats['FTA'] != 0 else 0
    stats['3p%'] = (stats['FG3M'] / stats['FG3A']) * 100 if stats['FG3A'] != 0 else 0
    
    # Update stats with weighted averages
    for key in weighted_stats.keys():
        stats[key] = weighted_stats[key]
    
    return stats

# Function to evaluate a team score based on Roto categories and 'egp'
def evaluate_team_score(team_stats):
    roto_score = sum([
        team_stats['ppg'] * team_stats['egp'], 
        team_stats['rpg'] * team_stats['egp'], 
        team_stats['apg'] * team_stats['egp'],
        team_stats['spg'] * team_stats['egp'], 
        team_stats['bpg'] * team_stats['egp'], 
        team_stats['fg%'] * team_stats['egp'],
        team_stats['ft%'] * team_stats['egp'], 
        team_stats['3p%'] * team_stats['egp']
    ]) - 2 * (team_stats['TO'] * team_stats['egp'])
    return roto_score


    
# Function to simulate the draft
def simulate_draft(df, draft_order):
    teams = {name: [] for name in draft_order}
    available_players = set(df['Name'].values)

    # Loop through each round
    for round_order in itertools.cycle([draft_order, reversed(draft_order)]):
        for drafter in round_order:
            if drafter == 'me':
                best_scores = []  # To store best scores and corresponding player names

                # Simulate adding each available player to 'me' team
                for player in available_players:
                    temp_team = teams['me'] + [player]
                    my_stats = aggregate_team_stats(temp_team, df)
                    all_teams_stats = {name: aggregate_team_stats(team, df) for name, team in teams.items()}
                    my_score = evaluate_team_score(my_stats)
                    
                    best_scores.append((my_score, player))

                # Sort and get top 10 picks
                best_scores.sort(reverse=True)
                top_10_picks = [player for score, player in best_scores[:10]]
                
                print("Top 10 choices for you are:")
                for i, pick in enumerate(top_10_picks):
                    print(f"{i+1}. {pick}")

                # Let user select from top 10
                player_picked = input("Who did you pick?")
                if player_picked not in available_players:
                    # Find the top 5 most similar player names
                    closest_matches = process.extract(player_picked, available_players, limit=5)
                    print("Did you mean one of these players?")
                    for i, (player, score) in enumerate(closest_matches):
                        print(f"{i+1}. {player}")
                    selected = int(input("Select the number corresponding to your choice: ")) - 1
                    player_picked = closest_matches[selected][0]
                #selected_pick = top_10_picks[selected]

                # Update 'me' team and available players
                teams['me'].append(player_picked)
                available_players.remove(player_picked)
                
                print(f"You picked {player_picked}. Your current team is: {teams['me']}")
                
            else:
                player_picked = input(f"Who did {drafter} pick? ")
                if player_picked not in available_players:
                    # Find the top 5 most similar player names
                    closest_matches = process.extract(player_picked, available_players, limit=5)
                    print("Did you mean one of these players?")
                    for i, (player, score) in enumerate(closest_matches):
                        print(f"{i+1}. {player}")
                    selected = int(input("Select the number corresponding to your choice: ")) - 1
                    player_picked = closest_matches[selected][0]
                teams[drafter].append(player_picked)
                available_players.remove(player_picked)
                
                print(f"{drafter} picked {player_picked}. Their current team is: {teams[drafter]}")
            team_stats = aggregate_team_stats(teams[drafter], df)
            print(f"{drafter}'s expected season stats: {team_stats}")


if __name__ == "__main__":
    df = pd.read_csv('all_player_stats.csv')
    draft_order = input("Enter the draft order separated by commas: ").strip().split(",")
    simulate_draft(df, draft_order)
