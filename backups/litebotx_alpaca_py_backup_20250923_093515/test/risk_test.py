from core.risk import calculate_position_size, calculate_position_size_with_stop

balance = 10000
risk_per_trade = 0.02
entry_price = 100
stop_price = 95

print("Risk Management Simulation Test Results:")

size_basic = calculate_position_size(balance, risk_per_trade, entry_price)
print(f"Basic position size: {size_basic}")

size_stop = calculate_position_size_with_stop(balance, risk_per_trade, entry_price, stop_price)
print(f"Position size with stop-loss: {size_stop}")

# Edge case tests
print("Edge case tests:")
print("Zero balance:", calculate_position_size(0, risk_per_trade, entry_price))
print("Zero risk:", calculate_position_size(balance, 0, entry_price))
print("Zero price:", calculate_position_size(balance, risk_per_trade, 0))
print("Zero stop distance:", calculate_position_size_with_stop(balance, risk_per_trade, entry_price, entry_price))