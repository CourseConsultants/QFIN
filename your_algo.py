from base import Exchange, Trade, Order, Product, Msg, Rest
from typing import List, Dict
import numpy as np
from collections import deque
import numpy as np
from typing import Dict, List


class PlayerAlgorithm:
    def __init__(self, products): 
        self.products = products
        self.name = "TT5"
        self.team_members = ["Nick", "Chelsea"]

        # Position tracking
        self.positions = {product.ticker: 0 for product in products}
        self.positions["Cash"] = 0  # realized PnL
        self.predicted_positions = {product.ticker: 0 for product in products}

        self.open_orders = {}
        self.mapping = {"Buy": 1, "Sell": -1}
        self.idx = 0
        self.timestamp_num = 0

        # Market data history
        self.bids = {p.ticker: [] for p in products}
        self.asks = {p.ticker: [] for p in products}
        self.mid_prices = {p.ticker: deque(maxlen=1000) for p in products}
        self.momentum = {p.ticker: deque(maxlen=1000) for p in products}
        self.rolling_corr = {p.ticker: deque(maxlen=1000) for p in products}

        # Rolling correlation incremental sums
        self.rolling_window_size = 50
        self.rolling_window = {p.ticker: deque(maxlen=self.rolling_window_size) for p in products}
        self.rolling_sum_x = {p.ticker: 0.0 for p in products}
        self.rolling_sum_y = {p.ticker: 0.0 for p in products}
        self.rolling_sum_x2 = {p.ticker: 0.0 for p in products}
        self.rolling_sum_y2 = {p.ticker: 0.0 for p in products}
        self.rolling_sum_xy = {p.ticker: 0.0 for p in products}

    def process_trades(self, trades: List[Trade]) -> None:
        for trade in trades:
        # If this bot was the aggressor (sent the order)
            if trade.agg_bot == self.name:
                self.positions[trade.ticker] += trade.size * self.mapping[trade.agg_dir] 
                self.positions["Cash"] -= trade.size * trade.price * self.mapping[trade.agg_dir] 
            elif trade.rest_bot == self.name: 
                self.positions[trade.ticker] -= trade.size * self.mapping[trade.agg_dir] 
                self.positions["Cash"] += trade.size * trade.price * self.mapping[trade.agg_dir] # =================In play_game.py============== pnl = player_bot.positions["Cash"]

            # Adjust predicted positions for our open orders
            order_id = getattr(trade, "order_id", None)
            if order_id is not None and order_id in self.open_orders:
                order_info = self.open_orders[order_id]
                filled_size = min(order_info['size'], trade.size)
                self.predicted_positions[trade.ticker] -= filled_size
                order_info['size'] -= filled_size
                if order_info['size'] <= 0:
                    del self.open_orders[order_id]

    def getMyPosition(self, ticker: str) -> int:
        return self.positions.get(ticker, 0)

    def send_messages(self, book: Dict[str, Dict[str, List["Rest"]]]) -> List["Msg"]:
        messages = []
        window = 50
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
            # --- Rolling correlation calculation (incremental) ---
            x_new = self.momentum[ticker][-1]
            if len(self.mid_prices[ticker]) >= 2 and self.mid_prices[ticker][-1] is not None and self.mid_prices[ticker][-2] is not None:
                y_new = self.mid_prices[ticker][-1] - self.mid_prices[ticker][-2]
            else:
                y_new = 0.0

            window_deque = self.rolling_window[ticker]

# Remove oldest values if deque is full
            if len(window_deque) == self.rolling_window_size:
                 x_old, y_old = window_deque.popleft()
                 self.rolling_sum_x[ticker] -= x_old
                 self.rolling_sum_y[ticker] -= y_old
                 self.rolling_sum_x2[ticker] -= x_old**2
                 self.rolling_sum_y2[ticker] -= y_old**2
                 self.rolling_sum_xy[ticker] -= x_old * y_old

# Add new values
            window_deque.append((x_new, y_new))
            self.rolling_sum_x[ticker] += x_new
            self.rolling_sum_y[ticker] += y_new
            self.rolling_sum_x2[ticker] += x_new**2
            self.rolling_sum_y2[ticker] += y_new**2
            self.rolling_sum_xy[ticker] += x_new * y_new

# Compute correlation
            n = len(window_deque)
            if n > 1:
                 numerator = n*self.rolling_sum_xy[ticker] - self.rolling_sum_x[ticker]*self.rolling_sum_y[ticker]
                 denominator = ((n*self.rolling_sum_x2[ticker] - self.rolling_sum_x[ticker]**2) *
                                (n*self.rolling_sum_y2[ticker] - self.rolling_sum_y[ticker]**2))**0.5
                 corr = numerator / denominator if denominator != 0 else 0
            else:
                 corr = 0
            self.rolling_corr[ticker].append(corr)

    


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

                max_pos = 200
                min_pos = -200

                if position_signal == 1: 
                    allowed_size = min(order_size, max_pos -self.predicted_positions[ticker] )
                elif position_signal == -1:
                    allowed_size = min(order_size, self.predicted_positions[ticker] - min_pos)
                else:
                    allowed_size = 0

                projected_pos = real_pos + self.predicted_positions[ticker]

                if position_signal == 1 and projected_pos <200: #allowed_size 
                    
                    if allowed_size > 0:
                        self.predicted_positions[ticker] += allowed_size
                        msg, order_id = self.create_order(ticker, allowed_size, mid_price_rounded, "Buy")   
                        messages.append(msg)                    
                        self.open_orders[order_id] = {"ticker": ticker,"direction": "Buy",  "size": allowed_size}
                elif position_signal == -1 and projected_pos>-200: #allowed_size 
                    
                    if allowed_size > 0:
                        self.predicted_positions[ticker] -= allowed_size
                        msg, order_id = self.create_order(ticker, allowed_size, mid_price_rounded, "Sell")  
                        messages.append(msg)
                        self.open_orders[order_id] = {"ticker": ticker,"direction": "Sell",  "size": allowed_size}
           
        for order_id, order_info in list(self.open_orders.items()):
                ticker2 = order_info["ticker"]
                direction = order_info["direction"]
                size = order_info["size"]
                price = order_info.get("price", None)
                mid = self.mid_prices[ticker2][-1]

                if self.predicted_positions[ticker2] >= 195 and direction == "Buy":
                    messages.append(self.remove_order(order_id))
                    self.predicted_positions[ticker2] -= size
                    del self.open_orders[order_id]
                elif self.predicted_positions[ticker2] <= -195 and direction == "Sell":
                    messages.append(self.remove_order(order_id))
                    self.predicted_positions[ticker2] += size
                    del self.open_orders[order_id]  
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
        new_message = Msg("REMOVE", order_idx)
        return new_message

    def set_idx(self, idx: int) -> None:
        self.idx = idx
