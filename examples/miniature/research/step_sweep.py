"""Tiny reproducible midpoint-rule sweep used by the miniature example."""

for n in (2, 4, 8):
    h = 1 / n
    estimate = h * sum(((i + 0.5) * h) ** 2 for i in range(n))
    error = abs(1 / 3 - estimate)
    print(f"n={n:2d} h={h:.3f} error={error:.10f}")
