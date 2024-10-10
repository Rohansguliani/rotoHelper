import csv

# Read the original CSV file
input_filename = 'all_player_stats.csv'
output_filename = 'players_with_estimates.csv'

players = []

with open(input_filename, 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        players.append(row)

# Process each player's stats and compute FTM, FTA, FGM, FGA
for player in players:
    try:
        # Convert string values to appropriate numeric types
        ppg = float(player['ppg'])
        fgp = float(player['fgp'])
        ftp = float(player['ftp'])
        three_pm = float(player['3pm'])

        FTr = 0.25  # Average league free throw rate

        # Step 1: Calculate Points from Three-Pointers
        points_3pm = three_pm * 3

        # Step 2: Calculate Adjusted PPG
        adjusted_ppg = ppg - points_3pm

        # Avoid division by zero
        if fgp == 0:
            C = 0
        else:
            # Step 3: Calculate Coefficient C
            C = (FTr * ftp) / fgp

        # Step 4: Compute Denominator
        denominator = 2 + C

        # Avoid division by zero
        if denominator == 0:
            two_pm = 0
        else:
            # Step 5: Compute Numerator
            numerator = adjusted_ppg - (three_pm * C)

            # Step 6: Calculate Two-Pointers Made
            two_pm = numerator / denominator

        # Ensure two_pm is not negative
        two_pm = max(two_pm, 0)

        # Step 7: Calculate Field Goals Made (FGM)
        fgm = three_pm + two_pm

        # Step 8: Calculate Field Goals Attempted (FGA)
        if fgp > 0:
            fga = fgm / fgp
        else:
            fga = 0

        # Step 9: Calculate Free Throw Attempts (FTA)
        fta = fga * FTr

        # Step 10: Calculate Free Throws Made (FTM)
        ftm = fta * ftp

        # Add new fields to the player dictionary
        player['ftm'] = round(ftm, 2)
        player['fta'] = round(fta, 2)
        player['fgm'] = round(fgm, 2)
        player['fga'] = round(fga, 2)

    except ValueError:
        # Handle cases where conversion to float fails
        player['ftm'] = ''
        player['fta'] = ''
        player['fgm'] = ''
        player['fga'] = ''

# Write the updated data to a new CSV file
fieldnames = ['Name', 'gp', 'min', 'fgp', 'ftp', '3pm', 'reb', 'ass', 'stl', 'bl', 'TOs', 'ppg', 'ftm', 'fta', 'fgm', 'fga']

with open(output_filename, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for player in players:
        writer.writerow(player)

print(f"New CSV file '{output_filename}' has been created with additional columns.")
