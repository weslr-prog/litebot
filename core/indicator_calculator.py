class IndicatorCalculator:
    def __init__(self):
        print("IndicatorCalculator initialized.")

    def compute(self, indicator_key, data):
        """
        Generic compute method for indicators.
        :param indicator_key: String identifier for the indicator type.
        :param data: Input data for calculation.
        :return: Computed indicator values.
        """
        if indicator_key == 'moving_average':
            return self.calculate_moving_average(data.get('values', []), data.get('window', 20))
        elif indicator_key == 'rsi':
            return self.calculate_rsi(data.get('values', []), data.get('period', 14))
        else:
            return f"Computed {indicator_key} for data"

    def calculate_moving_average(self, data, window):
        """
        Calculate the moving average for the given data and window size.
        :param data: List of numerical values.
        :param window: Window size for the moving average.
        :return: List of moving average values.
        """
        if len(data) < window:
            raise ValueError("Data length is less than the window size.")
        return [sum(data[i:i+window]) / window for i in range(len(data) - window + 1)]

    def calculate_rsi(self, data, period=14):
        """
        Calculate the Relative Strength Index (RSI) for the given data.
        :param data: List of numerical values.
        :param period: Period for RSI calculation.
        :return: List of RSI values.
        """
        if len(data) < period:
            raise ValueError("Data length is less than the period.")
        gains = [max(0, data[i] - data[i-1]) for i in range(1, len(data))]
        losses = [max(0, data[i-1] - data[i]) for i in range(1, len(data))]
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        rsi = []
        for i in range(period, len(data)):
            avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
            rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
            rsi.append(100 - (100 / (1 + rs)))
        return rsi