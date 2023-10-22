import pandas as pd
import itertools
from fuzzywuzzy import process


def calculate_dynamic_multipliers(all_teams_stats, my_team):
    default_multipliers = {'ppg': 1, 'rpg': 1, 'apg': 2, 'spg': 3, 'bpg': 3, 'TO': -2}
    avg_stats = {key: 0 for key in default_multipliers.keys()}
    num_teams = len(all_teams_stats)
    
    for team, stats in all_teams_stats.items():
        for key in avg_stats.keys():
            avg_stats[key] += stats[key] / num_teams

    my_team_ranks = {}
    for key in avg_stats.keys():
        ranks = sorted([(stats[key], team) for team, stats in all_teams_stats.items()], reverse=True)
        my_team_ranks[key] = [rank for rank, team in ranks].index(all_teams_stats[my_team][key]) + 1
    
    weak_categories = [key for key, rank in my_team_ranks.items() if rank > num_teams // 2]
    
    for key in weak_categories:
        default_multipliers[key] *= 1.5
    
    return default_multipliers


def aggregate_team_stats(team, df, teams):
    stats = {'fgm': 0, 'fga': 0, 'FTM': 0, 'FTA': 0, 'FG3M': 0, 'FG3A': 0, 'TO': 0, 'rpg': 0, 'apg': 0, 'spg': 0, 'bpg': 0, 'ppg': 0, 'egp':0}
    weighted_stats = {'ppg': 0, 'rpg': 0, 'apg': 0, 'spg': 0, 'bpg': 0, 'TO': 0}
    multipliers = {'ppg': 1, 'rpg': 1, 'apg': 2, 'spg': 3, 'bpg': 3, 'TO': -2}

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

    stats['fg%'] = (stats['fgm'] / stats['fga']) * 100 if stats['fga'] != 0 else 0
    stats['ft%'] = (stats['FTM'] / stats['FTA']) * 100 if stats['FTA'] != 0 else 0
    stats['3p%'] = (stats['FG3M'] / stats['FG3A']) * 100 if stats['FG3A'] != 0 else 0
    
    for key in weighted_stats.keys():
        stats[key] = weighted_stats[key]
    
    return stats

# Aggregate basic team stats for final results
def aggregate_base_team_stats(team, df):
    stats = {'ppg': 0, 'rpg': 0, 'apg': 0, 'spg': 0, 'bpg': 0, 'TO': 0}
    for player in team:
        player_stats = df[df['Name'] == player].iloc[0]
        for key in stats.keys():
            stats[key] += player_stats[key]
    return stats

# Display final draft results
def display_draft_results(teams, df):
    roto_cats = ['ppg', 'rpg', 'apg', 'spg', 'bpg', 'TO']
    final_stats = {team: aggregate_base_team_stats(players, df) for team, players in teams.items()}
    results_df = pd.DataFrame.from_dict(final_stats, orient='index', columns=roto_cats)
    print("Final Roto Table:")
    print(results_df)
    
    # Your team's expected numbers
    my_team_stats = final_stats['me']
    print("\nYour team's expected numbers:")
    for cat, value in my_team_stats.items():
        print(f"{cat}: {value}")

    # Calculate overall prediction rankings
    rankings = {cat: [] for cat in roto_cats}
    for cat in roto_cats:
        sorted_teams = sorted([(final_stats[team][cat], team) for team in teams.keys()], reverse=(cat != 'TO'))
        rankings[cat] = [team for score, team in sorted_teams]

    print("\nYour overall prediction rankings:")
    for cat, ranking in rankings.items():
        position = ranking.index('me') + 1
        print(f"{cat}: {position}")


def evaluate_team_score(team_stats):
    roto_score = sum([
        team_stats['ppg'], 
        team_stats['rpg'], 
        team_stats['apg'],
        team_stats['spg'], 
        team_stats['bpg'], 
        team_stats['fg%'],
        team_stats['ft%'], 
        team_stats['3p%']
    ]) - 1 * (team_stats['TO'])
    return roto_score


def simulate_draft(df, draft_order):
    teams = {name: [] for name in draft_order}
    available_players = set(df['Name'].values)

    for round_order in itertools.cycle([draft_order, reversed(draft_order)]):
        for drafter in round_order:
            if drafter == 'me':
                best_scores = []

                for player in available_players:
                    temp_team = teams['me'] + [player]
                    my_stats = aggregate_team_stats(temp_team, df, teams)
                    my_score = evaluate_team_score(my_stats)
                    
                    best_scores.append((my_score, player))

                best_scores.sort(reverse=True)
                top_10_picks = [player for score, player in best_scores[:10]]
                
                print("Top 10 choices for you are:")
                for i, pick in enumerate(top_10_picks):
                    print(f"{i+1}. {pick}")

                player_picked = input("Who did you pick?")
                if player_picked == 'END_DRAFT':
                    display_draft_results(teams, df)
                    return
                if player_picked not in available_players:
                    closest_matches = process.extract(player_picked, available_players, limit=5)
                    print("Did you mean one of these players?")
                    for i, (player, score) in enumerate(closest_matches):
                        print(f"{i+1}. {player}")
                    selected = int(input("Select the number corresponding to your choice: ")) - 1
                    player_picked = closest_matches[selected][0]

                teams['me'].append(player_picked)
                available_players.remove(player_picked)
                
                print(f"You picked {player_picked}. Your current team is: {teams['me']}")
                
            else:
                player_picked = input(f"Who did {drafter} pick? ")
                if player_picked == 'END_DRAFT':
                    display_draft_results(teams, df)
                    return
                if player_picked not in available_players:
                    closest_matches = process.extract(player_picked, available_players, limit=5)
                    print("Did you mean one of these players?")
                    for i, (player, score) in enumerate(closest_matches):
                        print(f"{i+1}. {player}")
                    selected = int(input("Select the number corresponding to your choice: ")) - 1
                    player_picked = closest_matches[selected][0]
                teams[drafter].append(player_picked)
                available_players.remove(player_picked)
                
                print(f"{drafter} picked {player_picked}. Their current team is: {teams[drafter]}")
            
            team_stats = aggregate_team_stats(teams[drafter], df, teams)
            #print(f"{drafter}'s expected season stats: {team_stats}")


if __name__ == "__main__":
    df = pd.read_csv('all_player_stats.csv')
    draft_order = input("Enter the draft order separated by commas: ").strip().split(",")
    simulate_draft(df, draft_order)
