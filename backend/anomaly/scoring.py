import statistics


def calculate_z_score(
    current_value: int,
    historical_values: list[int],
) -> float:

    if len(historical_values) < 2:
        return 0.0

    mean = statistics.mean(historical_values)

    try:
        std_dev = statistics.stdev(historical_values)
    except statistics.StatisticsError:
        return 0.0

    if std_dev == 0:
        return 0.0

    return (current_value - mean) / std_dev