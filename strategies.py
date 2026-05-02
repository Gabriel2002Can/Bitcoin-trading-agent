def dca(param = 1.0, value = 500):
    return value * param

def trigger_stop_loss(current_price, stop_loss):
    return current_price <= stop_loss

# -> This is the pseudo-code
# def tick(config -> obj, data -> obj) -> None:

#     dca_value, swing_signal = evaluate_strategies(metrics, config)

#     result = execute_strategies(dca_value, swing_value)

#     notify(result)

#     return None

def evaluate_strategies(metrics, config):
    pass

class TradingAgent:

    def __init__(self):
        pass