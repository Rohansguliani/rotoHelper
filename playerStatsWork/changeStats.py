import pandas as pd

def search_player(df, player_name):
    # Search for the player by name
    player_data = df[df['Name'].str.lower() == player_name.lower()]
    if len(player_data) == 0:
        print("Player not found.")
        return None
    return player_data

def print_stats(player_data):
    # Print player stats to 2 decimal places
    for column in player_data.columns:
        value = player_data.iloc[0][column]
        if isinstance(value, float) or isinstance(value, int):
            print(f"{column}: {value:.2f}")
        else:
            print(f"{column}: {value}")

def update_stat(df, player_data, stat_to_update, new_value):
    # Update the specific stat of the player
    index = player_data.index[0]
    df.at[index, stat_to_update] = new_value

    # If 'fgm' or 'fga' are updated, recalculate 'fg%'
    if stat_to_update in ['fgm', 'fga']:
        recalculate_fg_percent(df, index)

    if stat_to_update in ['ftm', 'fta']:
        recalculate_ft_percent(df, index)

    if stat_to_update in ['FG3M', 'FG3A']:
        recalculate_3p_percent(df, index)

def recalculate_fg_percent(df, index):
    # Recalculate 'fg%' using the formula: (fgm / fga) * 100
    fgm = df.at[index, 'fgm']
    fga = df.at[index, 'fga']
    
    # Check for divide-by-zero scenario
    if fga != 0:
        fg_percent = (fgm / fga) * 100
    else:
        fg_percent = 0

    # Update 'fg%' in the DataFrame
    df.at[index, 'fg%'] = fg_percent

def recalculate_ft_percent(df, index):
    ftm = df.at[index, 'ftm']
    fta = df.at[index, 'fta']
    
    # Check for divide-by-zero scenario
    if fta != 0:
        ft_percent = (ftm / fta) * 100
    else:
        ft_percent = 0

    # Update 'fg%' in the DataFrame
    df.at[index, 'ft%'] = ft_percent

def recalculate_3p_percent(df, index):
    # Recalculate 'fg%' using the formula: (fgm / fga) * 100
    FG3M = df.at[index, 'FG3M']
    FG3A = df.at[index, 'FG3A']
    
    # Check for divide-by-zero scenario
    if FG3A != 0:
        FG3P = (FG3M / FG3A) * 100
    else:
        FG3P = 0

    # Update 'fg%' in the DataFrame
    df.at[index, '3PT%'] = FG3P


def main():
    # Read CSV into a DataFrame
    df = pd.read_csv("all_player_stats.csv")

    while True:
        # Ask for the player's name
        player_name = input("Enter the name of the player: ")
        
        # Search for the player
        player_data = search_player(df, player_name)
        
        if player_data is not None:
            print("Found the following stats for the player:")
            print_stats(player_data)
            
            # Ask for the stat to update
            stat_to_update = input("Enter the stat you want to change: ")
            
            if stat_to_update not in df.columns:
                print("Invalid stat.")
                continue
            
            # Ask for the new value
            new_value = float(input(f"Enter the new value for {stat_to_update}: "))
            
            # Update the stat
            update_stat(df, player_data, stat_to_update, new_value)
            
            # Save the updated DataFrame to CSV
            df.to_csv("all_player_stats.csv", index=False)
            
            print("Stat updated.")
        
        # Ask if the user wants to continue
        another = input("Do you want to update another player? (yes/no): ")
        if another.lower() != 'yes':
            break

if __name__ == "__main__":
    main()
