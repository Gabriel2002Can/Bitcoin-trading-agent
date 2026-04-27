def dca(param = 1.0, value = 500):
    return value * param

def trigger_stop_loss(current_price, stop_loss):
    return current_price <= stop_loss

# -> This is the pseudo-code
# def tick(config, state, data):
#     metrics = compute_metrics(data)

#     dca_signal = evaluate_dca(metrics, state, config)
#     swing_signal = evaluate_swing(metrics, state, config)

#     decision = resolve_signals(dca_signal, swing_signal, config, state)

#     if decision:
#         execute_trade(decision, state)

#     notify(decision)

#     return decision
