from configuration import Configuration
from metrics import Metrics

# def dca(param = 1.0, value = 500):
#     return value * param

# def trigger_stop_loss(current_price, stop_loss):
#     return current_price <= stop_loss

class TradingAgent:
    """Uses metrics and the current configurations to evaluate which strategy should be used and its paramethers.
    """

    def __init__(self, configuration: Configuration, metrics: Metrics):
        self.configuration = configuration
        self.metrics = metrics

    def evaluate_strategies(self):
        # get configs; get metrics; get model opinion; formulate a total value to each return variable (dca_value and swing_value)
        pass

    def execute_strategies(self):
        # get the final report from the evaluate_strategies, return the final decision
        pass

    def notify(self):
        # notify the final report via telegram and gmail
        pass

    def tick(self):
        
        dca_value, swing_value = self.evaluate_strategies()

        result = self.execute_strategies(dca_value, swing_value)

        self.notify(result)

        return None