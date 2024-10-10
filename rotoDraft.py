import pandas as pd
import numpy as np
from fuzzywuzzy import process

# Function to calculate z-scores for players
def calculate_z_scores(df, categories):
    z_scores = pd.DataFrame()
    for cat in categories:
        if cat in ['fg%', 'ft%']:
            continue  # Skip percentages for now
        mean = df[cat].mean()
        std = df[cat].std()
        if std == 0:
            z_scores[cat] = 0
        else:
            z_scores[cat] = (df[cat] - mean) / std
    # Handle percentages separately
    for cat in ['fg%', 'ft%']:
        mean = df[cat].mean()
        std = df[cat].std()
        if std == 0:
            z_scores[cat] = 0
        else:
            z_scores[cat] = (df[cat] - mean) / std
    # Turnovers are minimized
    if 'TOs' in z_scores.columns:
        z_scores['TOs'] = -z_scores['TOs']  # Since fewer turnovers are better
    # Sum z-scores across all categories
    z_scores['total_z'] = z_scores.sum(axis=1)
    df['total_z'] = z_scores['total_z']
    return df

# Function to aggregate team statistics
def aggregate_team_stats(team, df):
    stats = {
        'fgm': 0.0, 'fga': 0.0, 'ftm': 0.0, 'fta': 0.0,
        '3pm': 0.0, 'reb': 0.0, 'ass': 0.0, 'stl': 0.0,
        'bl': 0.0, 'TOs': 0.0, 'ppg': 0.0
    }
    for player in team:
        player_stats = df[df['Name'] == player]
        if player_stats.empty:
            continue  # Skip if player not found
        player_stats = player_stats.iloc[0]
        for key in stats.keys():
            stats[key] += float(player_stats[key])
    # Calculate percentages
    stats['fg%'] = (stats['fgm'] / stats['fga']) * 100 if stats['fga'] != 0 else 0
    stats['ft%'] = (stats['ftm'] / stats['fta']) * 100 if stats['fta'] != 0 else 0
    return stats

# Function to calculate roto standings
def calculate_roto_standings(teams_stats):
    categories = ['ppg', 'reb', 'ass', 'stl', 'bl', 'fg%', 'ft%', '3pm', 'TOs']
    teams_scores = {team: {} for team in teams_stats.keys()}
    # Prepare category data
    category_data = {cat: [] for cat in categories}
    for team, stats in teams_stats.items():
        for cat in categories:
            value = stats.get(cat, 0)
            if cat == 'TOs':
                category_data[cat].append((team, -value))  # Negative because TOs are minimized
            else:
                category_data[cat].append((team, value))
    # Rank teams in each category
    for cat in categories:
        # Handle possible NaN values
        category_values = [(team, value if not np.isnan(value) else 0) for team, value in category_data[cat]]
        category_values.sort(key=lambda x: x[1], reverse=True)
        for rank, (team, value) in enumerate(category_values, start=1):
            teams_scores[team][cat] = len(teams_stats) - rank + 1  # Higher value gets higher rank
    return teams_scores

# Function to evaluate total roto score
def evaluate_roto_score(team_scores):
    total_score = sum(team_scores.values())
    return total_score

# Function to calculate combined score with dynamic weighting
def calculate_combined_score(z_score, roto_score, current_round, total_rounds):
    # Determine weights based on the current round
    if current_round <= 6:
        z_weight = 0.7
        roto_weight = 0.3
    else:
        # After round 6, flip the weights
        z_weight = 0.3
        roto_weight = 0.7
    # Alternatively, weights can be dynamically adjusted based on the round number
    # z_weight = max(0.1, 1 - (current_round / total_rounds))
    # roto_weight = 1 - z_weight
    # Normalize the roto_score to a 0-1 scale
    roto_score_normalized = roto_score / (9 * total_teams)
    combined_score = (z_weight * z_score_normalized(z_score)) + (roto_weight * roto_score_normalized)
    return combined_score

def z_score_normalized(z_score):
    # Normalize z-score to a 0-1 scale based on expected z-score range
    # Assuming z-scores range from -5 to +10 in this dataset
    z_min, z_max = -5, 10
    return (z_score - z_min) / (z_max - z_min)

# Function to suggest top picks based on different rankings
def suggest_top_picks(my_team, available_players, teams, df, current_round, num_suggestions=10, total_rounds=13):
    # Initialize list to store suggestions
    suggestions = []
    teams_stats = {name: aggregate_team_stats(team, df) for name, team in teams.items()}

    # Precompute opponents' stats to save time
    opponents = {name: stats for name, stats in teams_stats.items() if name != 'me'}

    # Iterate over available players
    for player in available_players:
        # Get player's z-score
        player_z = df[df['Name'] == player]['total_z'].values[0]
        # Create a temporary team with the player added
        temp_team = my_team + [player]
        teams_stats_temp = teams_stats.copy()
        teams_stats_temp['me'] = aggregate_team_stats(temp_team, df)
        # Calculate roto standings
        teams_scores = calculate_roto_standings(teams_stats_temp)
        my_roto_score = evaluate_roto_score(teams_scores['me'])
        # Determine your projected ranking
        total_scores = [(name, evaluate_roto_score(scores)) for name, scores in teams_scores.items()]
        total_scores.sort(key=lambda x: x[1], reverse=True)
        my_rank = [i+1 for i, (name, score) in enumerate(total_scores) if name == 'me'][0]
        # Calculate combined score
        combined_score = calculate_combined_score(player_z, my_roto_score, current_round, total_rounds)
        suggestions.append({
            'player': player,
            'roto_score': my_roto_score,
            'rank': my_rank,
            'z_score': player_z,
            'combined_score': combined_score
        })
    # Generate three separate lists
    # List A: Ranked by projected roto score
    list_a = sorted(suggestions, key=lambda x: -x['roto_score'])[:num_suggestions]
    # List B: Ranked by player z-score
    list_b = sorted(suggestions, key=lambda x: -x['z_score'])[:num_suggestions]
    # List C: Combined ranking
    list_c = sorted(suggestions, key=lambda x: -x['combined_score'])[:num_suggestions]
    return list_a, list_b, list_c

# Simulate the draft
def simulate_draft(df, draft_order):
    num_teams = len(draft_order)
    global total_teams  # Make total_teams accessible in other functions
    total_teams = num_teams
    teams = {name.strip(): [] for name in draft_order}
    available_players = set(df['Name'].values)
    total_picks = len(df)  # Or set a fixed number of rounds
    picks_made = 0

    # Prepare the draft sequence for the number of rounds you want
    num_rounds = 13  # Typical roster size; adjust as needed
    total_rounds = num_rounds
    draft_sequence = []
    for round_number in range(1, num_rounds + 1):
        if round_number % 2 != 0:
            draft_sequence.extend([name.strip() for name in draft_order])
        else:
            draft_sequence.extend([name.strip() for name in reversed(draft_order)])

    # Start the draft
    current_pick = 0
    for drafter in draft_sequence:
        current_round = (current_pick // num_teams) + 1
        current_pick += 1
        if drafter == 'me':
            # Suggest top picks
            list_a, list_b, list_c = suggest_top_picks(
                teams['me'], available_players, teams, df, current_round, total_rounds
            )
            print(f"\nRound {current_round} - Your turn to pick!")
            print("\nTop suggestions for you (Ranked by Projected Roto Score Impact):")
            for idx, suggestion in enumerate(list_a):
                print(f"{idx+1}. {suggestion['player']} (Projected Roto Score: {suggestion['roto_score']}, "
                      f"Projected Rank: {suggestion['rank']}, Player Z-Score: {suggestion['z_score']:.2f})")
            print("\nTop suggestions for you (Ranked by Player Z-Score):")
            for idx, suggestion in enumerate(list_b):
                print(f"{idx+1}. {suggestion['player']} (Z-Score: {suggestion['z_score']:.2f}, "
                      f"Projected Roto Score: {suggestion['roto_score']}, Projected Rank: {suggestion['rank']})")
            print("\nTop suggestions for you (Combined Ranking):")
            for idx, suggestion in enumerate(list_c):
                print(f"{idx+1}. {suggestion['player']} (Combined Score: {suggestion['combined_score']:.4f}, "
                      f"Z-Score: {suggestion['z_score']:.2f}, Projected Roto Score: {suggestion['roto_score']})")
            # Let user select a player
            player_picked = input("Enter the name of the player you pick: ").strip()
            if player_picked not in available_players:
                # Find the top 5 most similar player names
                closest_matches = process.extract(player_picked, available_players, limit=5)
                print("Did you mean one of these players?")
                for i, (player, score) in enumerate(closest_matches):
                    print(f"{i+1}. {player}")
                selected = int(input("Select the number corresponding to your choice: ")) - 1
                player_picked = closest_matches[selected][0]
            # Update team and available players
            teams['me'].append(player_picked)
            available_players.remove(player_picked)
            print(f"You picked {player_picked}.")
        else:
            player_picked = input(f"Round {current_round} - {drafter}'s turn to pick. Who did they pick? ").strip()
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
            print(f"{drafter} picked {player_picked}.")

        # After each pick, calculate and display your projected roto score and ranking
        teams_stats = {name: aggregate_team_stats(team, df) for name, team in teams.items()}
        teams_scores = {name: evaluate_roto_score(scores) for name, scores in calculate_roto_standings(teams_stats).items()}
        sorted_scores = sorted(teams_scores.items(), key=lambda x: x[1], reverse=True)
        my_roto_score = teams_scores['me']
        my_rank = [i+1 for i, (name, score) in enumerate(sorted_scores) if name == 'me'][0]
        print(f"\nAfter this pick, your projected roto score is {my_roto_score} (out of {9 * num_teams}), "
              f"and your projected ranking is {my_rank}/{num_teams}.")

        # Display your current team stats after your pick
        if drafter == 'me':
            my_stats = teams_stats['me']
            print(f"\nYour team so far: {teams['me']}")
            print("Your aggregated team stats:")
            for stat, value in my_stats.items():
                if stat in ['fg%', 'ft%']:
                    print(f"{stat}: {value:.2f}%")
                else:
                    print(f"{stat}: {value:.2f}")

            # Show your category ranks
            my_category_ranks = calculate_roto_standings(teams_stats)['me']
            print("\nYour category ranks:")
            for cat, rank in my_category_ranks.items():
                print(f"{cat}: Rank {rank}")

if __name__ == "__main__":
    # Load the player data
    df = pd.read_csv('players_with_estimates.csv')
    # Ensure numerical columns are correctly typed
    numeric_cols = ['gp', 'min', 'fgp', 'ftp', '3pm', 'reb', 'ass', 'stl', 'bl', 'TOs', 'ppg',
                    'ftm', 'fta', 'fgm', 'fga']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Calculate percentages
    df['fg%'] = (df['fgm'] / df['fga']) * 100
    df['ft%'] = (df['ftm'] / df['fta']) * 100

    # Calculate z-scores for all players
    categories = ['ppg', 'reb', 'ass', 'stl', 'bl', '3pm', 'fg%', 'ft%', 'TOs']
    df = calculate_z_scores(df, categories)

    # Get the draft order
    draft_order_input = input("Enter the draft order separated by commas (include 'me' where appropriate): ")
    draft_order = draft_order_input.strip().split(",")
    simulate_draft(df, draft_order)