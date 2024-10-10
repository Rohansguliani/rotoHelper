import csv

# Read the CSV file
input_filename = 'players_with_estimates.csv'

players = []

with open(input_filename, 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        players.append(row)

# Define acceptable tolerances
percentage_tolerance = 0.01  # Allow 1% difference
ppg_tolerance = 0.5          # Allow 0.5 points difference

# Check each player's stats
for player in players:
    try:
        name = player['Name']
        ftp = float(player['ftp'])
        fgp = float(player['fgp'])
        ppg = float(player['ppg'])
        ftm = float(player['ftm'])
        fta = float(player['fta'])
        fgm = float(player['fgm'])
        fga = float(player['fga'])
        three_pm = float(player['3pm'])

        # Free Throw Percentage Check
        if fta != 0:
            calculated_ftp = ftm / fta
            if abs(calculated_ftp - ftp) > percentage_tolerance:
                print(f"FTP mismatch for {name}: Calculated {calculated_ftp:.3f}, Expected {ftp}")
        else:
            if ftp != 0:
                print(f"FTP mismatch for {name}: FTA is zero but FTP is {ftp}")

        # Field Goal Percentage Check
        if fga != 0:
            calculated_fgp = fgm / fga
            if abs(calculated_fgp - fgp) > percentage_tolerance:
                print(f"FGP mismatch for {name}: Calculated {calculated_fgp:.3f}, Expected {fgp}")
        else:
            if fgp != 0:
                print(f"FGP mismatch for {name}: FGA is zero but FGP is {fgp}")

        # Points Per Game Check
        # Points from 3-pointers
        points_3pm = three_pm * 3
        # Points from 2-pointers
        points_2pm = (fgm - three_pm) * 2
        # Points from free throws
        points_ftm = ftm
        # Total calculated points
        total_points = points_3pm + points_2pm + points_ftm

        if abs(total_points - ppg) > ppg_tolerance:
            print(f"PPG mismatch for {name}: Calculated {total_points:.2f}, Expected {ppg}")

    except ValueError as e:
        print(f"Value error for {player['Name']}: {e}")
    except KeyError as e:
        print(f"Missing data for {player['Name']}: {e}")
