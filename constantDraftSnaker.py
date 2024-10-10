import pandas as pd
import numpy as np
import heapq
import copy
import threading

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
            stats[key] += float(player_stats.get(key, 0))
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

# Class to represent a draft state
class DraftState:
    def __init__(self, our_team, available_players, round_number, pick_order, teams_rosters, teams_stats):
        self.our_team = our_team  # List of our players
        self.available_players = available_players  # Set of available players
        self.round_number = round_number
        self.pick_order = pick_order  # List of team names in pick order
        self.teams_rosters = teams_rosters  # Dict of teams' rosters
        self.teams_stats = teams_stats  # Dict of teams' aggregated stats
        # Evaluate projected roto score
        teams_scores = calculate_roto_standings(self.teams_stats)
        self.total_roto_score = evaluate_roto_score(teams_scores['OurTeam'])
        self.priority = -self.total_roto_score  # Negative because heapq is a min-heap
        # Store category rankings
        self.category_rankings = teams_scores['OurTeam']
        # Store second-best team info for sanity check
        total_scores = [(name, evaluate_roto_score(scores)) for name, scores in teams_scores.items()]
        total_scores.sort(key=lambda x: x[1], reverse=True)
        self.standings = total_scores
        if total_scores[0][0] != 'OurTeam':
            self.second_best_team = total_scores[0][0]
            self.second_best_score = total_scores[0][1]
        else:
            self.second_best_team = total_scores[1][0]
            self.second_best_score = total_scores[1][1]
        self.second_best_category_rankings = teams_scores[self.second_best_team]
        self.second_best_team_roster = self.teams_rosters[self.second_best_team]

    def __lt__(self, other):
        return self.priority < other.priority

# Function to simulate the draft using beam search with expanded search space
def simulate_draft_beam_search(df, draft_position, num_teams=10, beam_width=50, top_n=10):
    # Initialize variables
    draft_order = ['Team' + str(i+1) for i in range(num_teams)]
    draft_order[draft_position - 1] = 'OurTeam'  # Replace with our team
    num_rounds = 13

    # Generate the full draft sequence (snake draft)
    draft_sequence = []
    for round_number in range(1, num_rounds + 1):
        if round_number % 2 != 0:
            draft_sequence.extend(draft_order)
        else:
            draft_sequence.extend(draft_order[::-1])

    # Initial state
    initial_state = DraftState(
        our_team=[],
        available_players=set(df['Name'].values),
        round_number=1,
        pick_order=draft_order,
        teams_rosters={team: [] for team in draft_order},
        teams_stats={team: {} for team in draft_order}
    )

    # Beam search initialization
    beam = [initial_state]
    best_teams = []

    # Opponent pick probabilities
    opponent_pick_probs = [0.5, 0.3, 0.15, 0.05]  # Probabilities for top 4 players
    opponent_pick_probs += [0] * (top_n - len(opponent_pick_probs))  # Pad with zeros if necessary

    # Start beam search
    for pick_index, drafter in enumerate(draft_sequence):
        new_beam = []
        for state in beam:
            # Copy state to avoid modifying original
            state_copy = copy.deepcopy(state)
            # Update round number
            state_copy.round_number = (pick_index // num_teams) + 1

            if drafter == 'OurTeam':
                # Our pick
                # Consider top N available players based on total_z
                available_df = df[df['Name'].isin(state_copy.available_players)].copy()
                available_df.sort_values(by='total_z', ascending=False, inplace=True)
                top_players = available_df.head(top_n)['Name'].values

                for player in top_players:
                    new_state = copy.deepcopy(state_copy)
                    new_state.our_team.append(player)
                    new_state.available_players.remove(player)
                    # Update team rosters and stats
                    new_state.teams_rosters['OurTeam'] = new_state.our_team
                    new_state.teams_stats['OurTeam'] = aggregate_team_stats(new_state.our_team, df)
                    # Update state
                    new_state = DraftState(
                        our_team=new_state.our_team,
                        available_players=new_state.available_players,
                        round_number=new_state.round_number,
                        pick_order=new_state.pick_order,
                        teams_rosters=new_state.teams_rosters,
                        teams_stats=new_state.teams_stats
                    )
                    new_beam.append(new_state)
            else:
                # Opponent's pick
                if state_copy.available_players:
                    available_df = df[df['Name'].isin(state_copy.available_players)].copy()
                    available_df.sort_values(by='total_z', ascending=False, inplace=True)
                    top_opponent_players = available_df.head(top_n)['Name'].values
                    # Determine opponent pick based on probabilities
                    opponent_pick = np.random.choice(
                        top_opponent_players,
                        p=opponent_pick_probs[:len(top_opponent_players)] / np.sum(opponent_pick_probs[:len(top_opponent_players)])
                    )
                    state_copy.available_players.remove(opponent_pick)
                    # Add the player to the opponent's team
                    state_copy.teams_rosters[drafter].append(opponent_pick)
                    # Update opponent's team stats
                    state_copy.teams_stats[drafter] = aggregate_team_stats(state_copy.teams_rosters[drafter], df)
                    # Update our team's stats (unchanged)
                    state_copy.teams_rosters['OurTeam'] = state_copy.our_team
                    state_copy.teams_stats['OurTeam'] = aggregate_team_stats(state_copy.our_team, df)
                    # Update state
                    state_copy = DraftState(
                        our_team=state_copy.our_team,
                        available_players=state_copy.available_players,
                        round_number=state_copy.round_number,
                        pick_order=state_copy.pick_order,
                        teams_rosters=state_copy.teams_rosters,
                        teams_stats=state_copy.teams_stats
                    )
                new_beam.append(state_copy)

        # Prune beam to keep top K states
        beam = heapq.nsmallest(beam_width, new_beam)

    # Collect final teams
    for state in beam:
        if len(state.our_team) == num_rounds:
            best_teams.append(state)

    return best_teams

# Function to run simulations for all draft positions
def run_simulations(df, num_teams=10, beam_width=50, top_n=10):
    output_file = 'best_teams.txt'
    lock = threading.Lock()
    results = []

    def simulate_for_position(position):
        best_teams = simulate_draft_beam_search(df, position, num_teams, beam_width, top_n)
        for state in best_teams:
            entry = {
                'position': position,
                'team': state.our_team,
                'total_roto_score': state.total_roto_score,
                'category_rankings': state.category_rankings,
                'second_best_team': state.second_best_team,
                'second_best_team_roster': state.second_best_team_roster,
                'second_best_total_roto_score': state.second_best_score,
                'second_best_category_rankings': state.second_best_category_rankings,
                'team_stats': state.teams_stats['OurTeam']
            }
            with lock:
                results.append(entry)

    threads = []
    for position in range(1, num_teams + 1):
        t = threading.Thread(target=simulate_for_position, args=(position,))
        t.start()
        threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()

    # Now, sort results by total roto score in descending order
    results.sort(key=lambda x: x['total_roto_score'], reverse=True)

    # Write results to output file
    with open(output_file, 'w') as f:
        for entry in results:
            f.write(f"Total Roto Score: {entry['total_roto_score']}\n")
            f.write(f"Draft Position: {entry['position']}\n")
            f.write(f"Team: {entry['team']}\n")
            f.write(f"Category Rankings: {entry['category_rankings']}\n")
            f.write(f"Second Best Team: {entry['second_best_team']}\n")
            f.write(f"Second Best Team Roster: {entry['second_best_team_roster']}\n")
            f.write(f"Second Best Total Roto Score: {entry['second_best_total_roto_score']}\n")
            f.write(f"Second Best Category Rankings: {entry['second_best_category_rankings']}\n")
            f.write(f"Team Stats: {entry['team_stats']}\n")
            f.write("=" * 40 + "\n")

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

    # Run simulations
    run_simulations(df)
