import numpy as np
import logging
import os
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class PerformanceMetrics:
    def __init__(self):
        self.metrics = {
            "wins": 0,
            "losses": 0,
            "total_return": 0.0,
            "trades": 0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "returns": []
        }

    def update(self, trade_result, initial_balance):
        logging.info(f"Updating metrics for trade result: {trade_result}, initial_balance: {initial_balance}")
        try:
            if trade_result and "price" in trade_result:
                self.metrics["trades"] += 1
                trade_return = (trade_result["price"] - initial_balance) / initial_balance
                self.metrics["returns"].append(trade_return)
                self.metrics["total_return"] += trade_return

                if trade_return > 0:
                    self.metrics["wins"] += 1
                else:
                    self.metrics["losses"] += 1

                # Calculate max drawdown
                cumulative = np.cumsum(self.metrics["returns"])
                peak = np.maximum.accumulate(cumulative)
                drawdown = (cumulative - peak).min() if len(cumulative) > 0 else 0.0
                self.metrics["max_drawdown"] = drawdown

                # Calculate Sharpe ratio
                if len(self.metrics["returns"]) > 1:
                    avg_return = np.mean(self.metrics["returns"])
                    std_dev = np.std(self.metrics["returns"])
                    self.metrics["sharpe"] = avg_return / std_dev if std_dev != 0 else 0.0
                logging.info(f"Metrics updated: {self.metrics}")
        except Exception as e:
            logging.error(f"Error updating metrics: {e}", exc_info=True)

    def report(self):
        logging.info("Reporting performance metrics.")
        try:
            win_rate = self.metrics["wins"] / self.metrics["trades"] if self.metrics["trades"] else 0.0
            logging.info(f"Total Trades: {self.metrics['trades']}")
            logging.info(f"Win Rate: {win_rate:.2%}")
            logging.info(f"Total Return: {self.metrics['total_return']:.2f}")
            logging.info(f"Max Drawdown: {self.metrics['max_drawdown']:.2f}")
            logging.info(f"Sharpe Ratio: {self.metrics['sharpe']:.2f}")
            return self.metrics
        except Exception as e:
            logging.error(f"Error reporting metrics: {e}", exc_info=True)
            return self.metrics

    def save_to_csv(self, filename="performance_metrics.csv", results_dir="results"):
        logging.info(f"Saving metrics to CSV: {filename} in {results_dir}")
        try:
            os.makedirs(results_dir, exist_ok=True)
            file_path = os.path.join(results_dir, filename)
            # Flatten returns for CSV
            metrics_copy = self.metrics.copy()
            metrics_copy["returns"] = str(metrics_copy["returns"])
            df = pd.DataFrame([metrics_copy])
            df.to_csv(file_path, index=False)
            logging.info(f"Metrics saved to {file_path}")
        except Exception as e:
            logging.error(f"Error saving metrics to CSV: {e}", exc_info=True)
