import platform
import sys
import os
import pandas as pd
from base import Product
from your_algo import PlayerAlgorithm

#====================== Setup OS-specific run_game import ======================
original_sys_path = sys.path.copy()
current_dir = os.path.dirname(os.path.abspath(__file__))
os_name = platform.system()

if os_name == "Linux":
    sys.path.insert(0, os.path.join(current_dir, "bin/linux_version"))
    from bin.linux_version.game_setup import run_game
elif os_name == "Windows":
    sys.path.insert(0, os.path.join(current_dir, "bin/windows_version"))
    from bin.windows_version.game_setup import run_game
elif os_name == "Darwin":
    sys.path.insert(0, os.path.join(current_dir, "bin/mac_version"))
    from bin.mac_version.game_setup import run_game
else:
    raise ValueError("Unsupported OS")

print("Imports Completed")
sys.path = original_sys_path

# ====================== Simulation Parameters ======================
num_markets = 1 # Number of different markets
num_timestamps = 20000  # Timestamps per market

# Prepare storage for all markets
all_markets_data = []

# ====================== Run Simulation for Multiple Markets ======================
for market_idx in range(1, num_markets + 1):
    print(f"Running market {market_idx}/{num_markets}...")
    
    uec = Product("UEC", mpv=0.1, pos_limit=200, fine=20)
    products = [uec]
    
    player_bot = PlayerAlgorithm(products)
    
    pnl = run_game(player_bot, num_timestamps, products)
    
    # Collect bid/ask data
    uec_bids = player_bot.bids["UEC"]
    uec_asks = player_bot.asks["UEC"]
    
    # Save data for this market
    market_df = pd.DataFrame({
        "Market": market_idx,
        "Bids": uec_bids,
        "Asks": uec_asks
    })
    all_markets_data.append(market_df)

# ====================== Combine All Markets and Save ======================
full_df = pd.concat(all_markets_data, ignore_index=True)
print(pnl)
#csv_path = os.path.join(current_dir, "Test.csv")
#print("Saving CSV to:", csv_path)
#full_df.to_csv(csv_path, index=False)
print("All markets saved successfully!")
