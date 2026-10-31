"""Layout engine: band (strip) layout + CRAFT-style swap / simulated annealing.
Dept index i -> row i in R (x, y, w, h). Plot = W x H, origin bottom-left."""
import math
import random
import numpy as np


def initial_order(F):
    """CORELAP-style: start with highest-flow dept, add dept most tied to placed ones."""
    S = F + F.T
    tot = S.sum(1)
    order = [int(tot.argmax())]
    rest = set(range(len(F))) - set(order)
    while rest:
        nxt = max(rest, key=lambda j: (S[j, order].sum(), tot[j]))
        order.append(nxt)
        rest.remove(nxt)
    return order


def build(order, areas, W, H, n_bands):
    """Fill plot with serpentine bands; widths/heights proportional to area."""
    n = len(order)
    total = float(sum(areas[i] for i in order))
    target = total / n_bands
    bands, acc = [[]], 0.0
    for i in order:
        if acc >= target * len(bands) and len(bands) < n_bands:
            bands.append([])
        bands[-1].append(i)
        acc += areas[i]
    R = np.zeros((n, 4))
    y = 0.0
    for b, band in enumerate(bands):
        ba = float(sum(areas[i] for i in band))
        h = H * ba / total
        x = 0.0
        for i in (band if b % 2 == 0 else band[::-1]):
            w = W * areas[i] / ba
            R[i] = (x, y, w, h)
            x += w
        y += h
    return R


def evaluate(R, F, W, H, max_ar):
    S = F + F.T
    cen = R[:, :2] + R[:, 2:] / 2
    D = np.abs(cen[:, None, 0] - cen[None, :, 0]) + np.abs(cen[:, None, 1] - cen[None, :, 1])
    flow_cost = float((S * D).sum() / 2)
    ar = np.maximum(R[:, 2] / R[:, 3], R[:, 3] / R[:, 2])
    viol = float(np.maximum(0, ar - max_ar).sum())
    penalty = viol * (S.sum() / 2 + 1) * (W + H) / 10
    return flow_cost + penalty, flow_cost


def optimize(areas, F, W, H, bands=0, algo="CRAFT (swap)", iters=3000, max_ar=4.0, seed=1):
    areas = np.asarray(areas, float)
    F = np.asarray(F, float)
    n = len(areas)
    cands = [bands] if bands > 0 else list(range(1, min(n, 4) + 1))
    best = None
    for nb in cands:
        nb = min(nb, n)
        rng = random.Random(seed)

        def score(o):
            return evaluate(build(o, areas, W, H, nb), F, W, H, max_ar)[0]

        order = initial_order(F)
        cur = score(order)
        base = cur
        top = (cur, order[:])
        hist = [cur]
        if n >= 2:
            if algo.startswith("CRAFT"):
                for _ in range(iters):
                    bi = bj = None
                    bc = cur
                    for i in range(n):
                        for j in range(i + 1, n):
                            o = order[:]
                            o[i], o[j] = o[j], o[i]
                            c = score(o)
                            if c < bc - 1e-9:
                                bi, bj, bc = i, j, c
                    if bi is None:
                        break
                    order[bi], order[bj] = order[bj], order[bi]
                    cur = bc
                    hist.append(cur)
                top = (cur, order[:])
            else:  # simulated annealing
                T = cur * 0.1 + 1e-9
                alpha = (1e-3) ** (1 / max(iters, 1))
                for k in range(iters):
                    o = order[:]
                    i, j = rng.sample(range(n), 2)
                    o[i], o[j] = o[j], o[i]
                    c = score(o)
                    d = c - cur
                    if d < 0 or rng.random() < math.exp(-d / T):
                        order, cur = o, c
                        if cur < top[0]:
                            top = (cur, order[:])
                    T *= alpha
                    if k % 50 == 0:
                        hist.append(top[0])
        R = build(top[1], areas, W, H, nb)
        total, flow_cost = evaluate(R, F, W, H, max_ar)
        res = dict(order=top[1], bands=nb, R=R, cost=total, flow_cost=flow_cost,
                   base_cost=base, history=hist)
        if best is None or res["cost"] < best["cost"]:
            best = res
    return best
