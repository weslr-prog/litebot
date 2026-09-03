"""
Meta Learner (Q-Learner)
Purpose: Learn which strategy works best under certain conditions.
"""

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class MetaLearner:
    def __init__(self):
        # Define a simple mapping of regimes to strategies
        self.strategy_map = {
            "bull": "momentum",
            "bear": "mean_reversion",
            "sideways": "range_trading",
            "volatile": "volatility_breakout"
        }
        logging.info(f"MetaLearner initialized with strategy map: {self.strategy_map}")

    def decide_strategy(self, context):
        logging.info(f"Deciding strategy with context: {context}")
        try:
            regime = context.get("regime", "unknown")
            strategy = self.strategy_map.get(regime, None)
            if strategy:
                logging.info(f"Strategy selected for regime '{regime}': {strategy}")
            else:
                logging.warning(f"No strategy found for regime '{regime}'.")
            return strategy
        except Exception as e:
            logging.error(f"Error deciding strategy: {e}", exc_info=True)
            return None
