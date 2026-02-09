import datetime

import json
import os
from pathlib import Path

WEIGHTS_FILE = Path(__file__).parent / 'ai_weights.json'

class TradePredictor:
    def __init__(self):
        # Default Weights
        self.weights = [0.5, 0.5, 0.5, 0.5, -0.5, 0.5]
        self.learning_rate = 0.1
        
        # Load persistent weights if they exist
        self.load_weights()
        
        # Initial training on default data if no weights found
        if not WEIGHTS_FILE.exists():
             # User (time, sl, tp, rr, news, strategy, result)
            self.data = [
                (0.8, 0.2, 0.6, 0.7, 0, 0.8, 1),  # good London trade
                (0.3, 0.6, 0.4, 0.3, 1, 0.4, 0),  # bad news trade
                (0.9, 0.3, 0.7, 0.8, 0, 0.9, 1),
                (0.2, 0.7, 0.3, 0.2, 1, 0.3, 0),
                (0.7, 0.4, 0.6, 0.6, 0, 0.7, 1),
            ]
            self.train_batch(self.data)
            self.save_weights()

    def neuron(self, inputs, weights):
        total = 0
        for i, w in zip(inputs, weights):
            total += i * w
        return total

    def train_batch(self, dataset):
        for epoch in range(20):
            for row in dataset:
                inputs = list(row[:-1])
                correct = row[-1]
                self._learn_step(inputs, correct)

    def _learn_step(self, inputs, correct):
        prediction = self.neuron(inputs, self.weights)
        mistake = correct - prediction
        for i in range(len(self.weights)):
            self.weights[i] += self.learning_rate * mistake * inputs[i]

    def predict(self, inputs):
        return self.neuron(inputs, self.weights)
        
    def save_weights(self):
        try:
            with open(WEIGHTS_FILE, 'w') as f:
                json.dump(self.weights, f)
        except Exception as e:
            print(f"Error saving AI weights: {e}")
            
    def load_weights(self):
        if WEIGHTS_FILE.exists():
            try:
                with open(WEIGHTS_FILE, 'r') as f:
                    self.weights = json.load(f)
            except Exception as e:
                print(f"Error loading AI weights: {e}")

    def prepare_inputs(self, form=None, entry=None):
        # Heuristic mapping of form/entry data to [time, sl, tp, rr, news, strategy]
        
        # Helper to extract value safely
        def get_val(obj, attr, default=None):
            if hasattr(obj, attr):
                # Handle form data vs model data
                val = getattr(obj, attr)
                if hasattr(val, 'data'): return val.data # Form field
                return val
            return default

        # 1. Time
        time_val = 0.5
        date = get_val(form, 'date') or get_val(entry, 'date')
        if date and hasattr(date, 'hour'):
            time_val = date.hour / 24.0
        else:
             time_val = datetime.datetime.now().hour / 24.0
        
        # Helper to safely convert to float
        def safe_float(val):
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        # 2. SL / 3. TP
        entry_price = safe_float(get_val(form, 'entry_price') or get_val(entry, 'entry_price'))
        stop_loss = safe_float(get_val(form, 'stop_loss') or get_val(entry, 'stop_loss'))
        take_profit = safe_float(get_val(form, 'take_profit') or get_val(entry, 'take_profit'))

        sl_val = 0.5
        if stop_loss is not None and entry_price is not None and entry_price != 0:
             dist = abs(entry_price - stop_loss)
             sl_val = min(dist / entry_price * 100, 1.0)
             
        tp_val = 0.5
        if take_profit is not None and entry_price is not None and entry_price != 0:
             dist = abs(entry_price - take_profit)
             tp_val = min(dist / entry_price * 100, 1.0)

        # 4. RR
        rr_raw = safe_float(get_val(form, 'risk_reward') or get_val(entry, 'risk_reward'))
        rr_val = 0.5
        if rr_raw is not None:
             rr_val = min(rr_raw / 5.0, 1.0)
        
        # 5. News
        news_event = get_val(form, 'news_event') or get_val(entry, 'news_event')
        news_val = 1.0 if news_event else 0.0
        
        # 6. Strategy
        strategy = get_val(form, 'strategy') or get_val(entry, 'strategy')
        strat_val = 0.5
        if strategy:
            strat_val = (hash(strategy) % 100) / 100.0
            
        return [time_val, sl_val, tp_val, rr_val, news_val, strat_val]

    def learn_from_entry(self, entry):
        # Only learn if we have a definitive result
        if not entry.result: return
        
        # Map Result to Target (1 = Win, 0 = Loss/BE)
        # Simplify: Win=1, Loss=0, BE=0.5? User code used 0/1.
        target = 1.0 if entry.result.lower() == 'win' else 0.0
        if entry.result.lower() == 'be': target = 0.5
        
        inputs = self.prepare_inputs(entry=entry)
        
        # Online Learning (Update weights based on this one sample)
        # We can run a few iterations or just one step for SGD
        self._learn_step(inputs, target)
        self.save_weights()

predictor = TradePredictor()
