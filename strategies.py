def dca(param = 1.0, value = 500):
    return value * param

def trigger_stop_loss(current_price, stop_loss):
    return current_price <= stop_loss
