from base import Exchange, Trade, Order, Product, Msg, Rest
from typing import List, Dict
import numpy as np
from collections import deque
import numpy as np
from typing import Dict, List


class PlayerAlgorithm:
    """
    Main trcading algorithm class that implements the player's trading strategy.
    
    This class handles all trading decisions, order management, and market analysis
    for a single trading bot in the exchange simulation.
    """
    
    def __init__(self, products: List[Product]):
        """
        Initialize the trading algorithm with available products and basic configuration.
        
        Args:
            products: List of all tradeable products available in the current round
        """
        self.products = products        # A list of all tradeable products in the current round
        self.name = "TT5"   # The name representing your bot in the trade logs  
        self.timestamp_num = 0          # Counter to track the number of timestamps completed
        self.team_members=["Nick", "Chelsea"]

        self.bids = {product.ticker: [] for product in products}
        self.asks = {product.ticker: [] for product in products}

        self.mid_prices = {product.ticker: deque(maxlen=1000) for product in products}
        self.momentum = {product.ticker: deque(maxlen=1000) for product in products}
        self.rolling_corr = {product.ticker: deque(maxlen=1000) for product in products}
        self.position = {product.ticker: 0 for product in products}
        self.predicted_positions = {product.ticker: 0 for product in products}
        self.idx=0
        self.open_orders = {} 

        



        # Slight change to create a dictionary with the bids or asks for every single stock -> scales for future weeks
        # Initialize any other global variables you may need here
        # Examples: position tracking, risk management parameters, strategy state variables
    def getMyPosition(self, ticker: str) -> int:
        return self.position.get(ticker, 0)
    
    def process_trades(self, trades: List[Trade]) -> None:
        for trade in trades:
        # If this bot was the aggressor (sent the order)
            if trade.agg_bot == self.name:
                print("You did a trade!")
                #print(f"[TRADE] Ticker={trade.ticker}, AggDir={trade.agg_dir}, "
                      #f"RestDir={trade.rest_dir}, Size={trade.size}, "
                      #f"NewPosition={self.getMyPosition(trade.ticker)}")
                if trade.agg_dir == "Buy":
                    self.position[trade.ticker] += trade.size
                    
                     
                elif trade.agg_dir == "Sell":
                    self.position[trade.ticker] -= trade.size
                    
                    

        # If this bot was the resting order (got hit)
            if trade.rest_bot == self.name:
                print("You did a trade!")
                #print(f"[TRADE] Ticker={trade.ticker}, AggDir={trade.agg_dir}, "
                      #f"RestDir={trade.rest_dir}, Size={trade.size}, "
                      #f"NewPosition={self.getMyPosition(trade.ticker)}")
                if trade.agg_dir == "Buy":
                    self.position[trade.ticker] += trade.size
                    
                    
                elif trade.agg_dir == "Sell":
                    self.position[trade.ticker] -= trade.size
                    
                   

    # Clamp to position limits just in case
      
            #print(f"[CLAMP] Ticker={ticker}, ClampedPosition={self.position[ticker]}")

    
    """
        Processes completed trades and updates internal state accordingly.
        
        This method is called after each bot turn with a list of all trades
        that occurred. Use this to:
        - Track your trading performance
        - Update position information
        - Analyze market activity
        - etc.
        
        Args:
            trades: List of Trade objects representing all completed trades in the most recent bot turn
        
        Note:
            - Bot names are anonymized except for your own
            - Order IDs are hidden except for your own
     
         Optimized trading logic:
     - Updates only the *latest* bid, ask, mid, momentum, and rolling correlation
     - Avoids recalculating entire histories each tick

        Main trading logic method that analyzes the order book and generates trading decisions.
        
        This method is called on each trading cycle and should implement your core trading strategy.
        It analyzes the current market state and returns a list of messages to send to the exchange.
        
        Args:
            book: Complete order book structure organized as:
                  {ticker: {Bid: [resting_orders], Ask: [resting_orders]}}
                  - ticker: Product identifier (e.g., "UEC")
                  - Bid: List of resting buy orders (descending price order - highest bid first)
                  - Ask: List of resting sell orders (ascending price order - lowest ask first)
                  - resting_orders: List of Rest objects representing pending orders
        
        Returns:
            List[Msg]: List of messages to send to the exchange (orders, cancellations, etc.)
        

    
        This method returns a list of Msg objects you want to send to the exchange.
        There are two types of messages you may want to send: 

        1. Sending an order (Msg with "ORDER" type and Order object)
        2. Removing an order (Msg with "REMOVE" type and order ID)
        
        When sending an order, your Msg object should be created with:
        - First argument: the string "ORDER"
        - Second argument: an Order object with your desired trade parameters
        
        When removing an order, your Msg object should be created with:
        - First argument: the string "REMOVE" 
        - Second argument: the ID of the order you want to cancel

        To make sending and removing orders easier, we have provided the helper functions:
        - create_order(): Creates a new order message
        - remove_order(): Creates a cancel order message
    """
    def send_messages(self, book: Dict[str, Dict[str, List["Rest"]]]) -> List["Msg"]:
        messages = []
        window = 20
        order_size = 5
        mpv = 0.1  # minimum price variation (tick size)
        for ticker in book:
        # --- Extract top-of-book prices ---
            best_bid = book[ticker]["Bids"][0].price if book[ticker]["Bids"] else None
            best_ask = book[ticker]["Asks"][0].price if book[ticker]["Asks"] else None

        # --- Mid price calculation ---
            if best_bid is not None and best_ask is not None:
                new_mid = (best_bid + best_ask) / 2
                mid_price_rounded = round(new_mid / mpv) * mpv
            else:
                new_mid = None
                mid_price_rounded = None

        # --- Append mid price ---
            self.mid_prices[ticker].append(new_mid)

        # --- Momentum calculation ---
            if len(self.mid_prices[ticker]) >= 2:
                m = self.mid_prices[ticker][-1] - self.mid_prices[ticker][-2] \
                    if self.mid_prices[ticker][-1] is not None and self.mid_prices[ticker][-2] is not None else 0
                self.momentum[ticker].append(m)
            else:
                self.momentum[ticker].append(0)

        # --- Rolling correlation calculation ---
            if len(self.momentum[ticker]) >= window and len(self.mid_prices[ticker]) > window:
                m_window = list(self.momentum[ticker])[-window:]
                f_window = [
                    self.mid_prices[ticker][i+1] - self.mid_prices[ticker][i]
                    for i in range(len(self.mid_prices[ticker]) - window - 1,
                                   len(self.mid_prices[ticker]) - 1)
                    if self.mid_prices[ticker][i] is not None and self.mid_prices[ticker][i+1] is not None
                ]
                corr = np.corrcoef(m_window, f_window)[0, 1] if len(f_window) == len(m_window) and len(f_window) > 1 else 0
                self.rolling_corr[ticker].append(corr)
            else:
                self.rolling_corr[ticker].append(0)

        # --- Trading signal ---
            last_momentum = self.momentum[ticker][-1]
            last_corr = self.rolling_corr[ticker][-1]
            position_signal = 0
            if last_momentum > 0 and last_corr > 0:
                position_signal = 1  # buy
            elif last_momentum < 0 and last_corr > 0:
                position_signal = -1  # sell

        # --- Position limit enforcement ---
        
            
            


            if mid_price_rounded is not None:
                real_pos=self.getMyPosition(ticker)
                print(real_pos)

                max_pos = 200
                min_pos = -200



                if position_signal == 1: 
                    allowed_size = min(order_size, max_pos -self.predicted_positions[ticker] )
                elif position_signal == -1:
                    allowed_size = min(order_size, self.predicted_positions[ticker] - min_pos)
                else:
                    allowed_size = 0

                projected_pos = real_pos + self.predicted_positions[ticker]

                if position_signal == 1 and projected_pos + allowed_size<200:
                    
                    if allowed_size > 0:
                        msg, order_id = self.create_order(ticker, allowed_size, mid_price_rounded, "Buy")   
                        messages.append(msg)                    


                        self.predicted_positions[ticker] += allowed_size
                        self.open_orders[order_id] = {"ticker": ticker,"direction": "Buy",  "size": allowed_size}
                elif position_signal == -1 and projected_pos + allowed_size >-200:
                    
                    if allowed_size > 0:
                        msg, order_id = self.create_order(ticker, allowed_size, mid_price_rounded, "Sell")  

                     
                        messages.append(msg)
                        self.predicted_positions[ticker] -= allowed_size
                        self.open_orders[order_id] = {"ticker": ticker,"direction": "Sell",  "size": allowed_size}

            for order_id, order_info in list(self.open_orders.items()):
                ticker = order_info["ticker"]
                direction = order_info["direction"]
                size = order_info["size"]
                if self.predicted_positions[ticker] >= 190 and direction == "Buy":
                    messages.append(self.remove_order(order_id))
                    self.predicted_positions[ticker] -= size  # <-- update predicted
                    del self.open_orders[order_id]
                elif self.predicted_positions[ticker] <= -190 and direction == "Sell":
                    messages.append(self.remove_order(order_id))
                    self.predicted_positions[ticker] += size  # <-- update predicted
                    del self.open_orders[order_id]

            



            
            
            print(f"[DEBUG] {ticker}: RealPos={self.getMyPosition(ticker)}, "f"PredictedPos={self.predicted_positions[ticker]}")
            
                        

           
           
        self.timestamp_num += 1
        return messages



    
    def display_book(self, book):
        for ticker in book:
            print(ticker)
            for side in book[ticker]:
                print(side)
                for order in book[ticker][side]:
                    print(f"{order.rest_dir}, Price: {order.price}, Size: {order.size}")

    def create_order(self, ticker: str, size: int, price: float, direction: str) -> Msg:
        """
        Creates a new order message for the exchange.
        
        This helper method constructs an Order object with the specified parameters
        and wraps it in a Msg object for transmission to the exchange.
        
        Args:
            ticker: Product symbol to trade (e.g., "UEC", "AAPL")
            size: Number of units to trade (positive integer)
            price: Price per unit (float)
            direction: Trade direction - "Buy" or "Sell"
        
        Returns:
            Msg: Message object containing the order for the exchange
        
        Note:
            Automatically assigns a unique order ID and increments the internal counter
        """
        order_idx = self.idx
        new_order = Order(
            ticker=ticker,
            price=price,
            size=size,
            order_id=order_idx,
            agg_dir=direction,
            bot_name=self.name,
        )
        new_message = Msg("ORDER", new_order)
        self.idx += 1
        return new_message, order_idx

    def remove_order(self, order_idx):
        """
        Creates a message to cancel/remove an existing order.
        
        Args:
            order_idx: The unique ID of the order to cancel
        
        Returns:
            Msg: Message object requesting order cancellation
        """
        new_message = Msg("REMOVE", order_idx)
        return new_message

    def set_idx(self, idx: int) -> None:
        """
        Sets the starting order ID for the current trading session.
        
        Each order requires a unique integer ID to track it through the system.
        You are responsible for generating these IDs, ensuring they are unique
        and fall within the valid range provided by the exchange.
        
        Args:
            idx: Starting order ID for this trading session
        
        Note:
            - Valid ID range: [idx, idx + 999999]
            - Each order ID must be unique within this range
            - Recommended approach: start with `idx` and increment by 1 for each order
            - This function initializes `self.idx` to the starting ID for the session
        """
        self.idx = idx

   