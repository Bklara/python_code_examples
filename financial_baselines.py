"""Simple baselines vs "smart" encoders for short-horizon return prediction.

A toy, numpy-only reproduction of the experimental protocol from
"Towards Financial World Modeling" (Merchant et al., arXiv:2610.09048):

* encoders turn a window of market "tokens" into a state vector;
* every encoder is frozen and evaluated with the same ridge linear probe;
* prediction quality = rank IC (cross-sectional Spearman between the
  prediction and the realised forward return), reported per market regime;
* latent geometry = effective dimensionality (participation ratio) and how
  well the embedding still encodes "who is this stock" (sector probe).

Baselines from the paper that are reproduced here:
    ridge_last24   - ridge regression on the last 24 raw input tokens
    random_encoder - untrained randomly initialised network + linear probe
compared against
    pca_ssl        - self-supervised "reconstruct the window" encoder (PCA)
    supervised     - MLP trained to predict the 15-step forward return
    multi_head     - MLP trained to predict several horizons at once

The data is synthetic (factor model with a weak, regime-dependent
predictable component), so absolute numbers mean nothing; the point is the
shape of the comparison: simple baselines are hard to beat, and the
encoder that predicts best is not the one with the richest latent space.

Usage:
    python financial_baselines.py --stocks 60 --steps 6000 --regimes 8
"""
import argparse
import logging

import numpy as np

logger = logging.getLogger('fin_baselines')

WINDOW = 64
HORIZON = 15
AUX_HORIZONS = (1, 5, 15, 30)


# --------------------------------------------------------------------------
# synthetic market
# --------------------------------------------------------------------------
def simulate_market(n_stocks, n_steps, n_regimes, n_sectors, rng):
    """Returns per-step returns, volumes, sector labels and regime ids."""
    sector = rng.integers(0, n_sectors, n_stocks)
    sector_vol = np.geomspace(0.4, 3.0, n_sectors)
    sector_ar = rng.uniform(-0.2, 0.2, n_sectors)
    beta = rng.normal(1.0, 0.3, n_stocks)

    regime = np.repeat(np.arange(n_regimes), int(np.ceil(n_steps / n_regimes)))[:n_steps]
    regime_vol = rng.uniform(0.6, 2.5, n_regimes)
    # strength of mean reversion of the last 20-step move; changes (and can
    # even flip into momentum) from one regime to the next
    regime_rev = rng.normal(0.012, 0.01, n_regimes)

    market = rng.standard_normal(n_steps) * regime_vol[regime]
    sector_f = rng.standard_normal((n_steps, n_sectors)) * regime_vol[regime, None] * 0.7

    returns = np.zeros((n_steps, n_stocks))
    idio = rng.standard_normal((n_steps, n_stocks)) * sector_vol[sector] * regime_vol[regime, None]
    for t in range(1, n_steps):
        move = returns[max(0, t - 20):t].sum(axis=0)
        returns[t] = (beta * market[t] + sector_f[t, sector] + idio[t]
                      + sector_ar[sector] * returns[t - 1]
                      - regime_rev[regime[t]] * move)
    returns *= 1e-3
    volume = np.log1p(np.abs(returns) * 1e3 + rng.exponential(1.0, returns.shape))
    return returns, volume, sector, regime


def make_tokens(returns, volume):
    """One token per step: (return, |return|, log-volume).

    Z-scored per feature over the whole market (not per stock), so stock-level
    volatility - and with it sector identity - stays visible to the encoders.
    """
    tok = np.stack([returns, np.abs(returns), volume], axis=-1)
    mu = tok.mean(axis=(0, 1), keepdims=True)
    sd = tok.std(axis=(0, 1), keepdims=True) + 1e-12
    return (tok - mu) / sd


def build_samples(tokens, returns, regime, stride):
    """Windows of WINDOW tokens with forward returns for several horizons."""
    n_steps, n_stocks, _ = tokens.shape
    max_h = max(AUX_HORIZONS)
    cum = np.vstack([np.zeros((1, n_stocks)), np.cumsum(returns, axis=0)])
    times = np.arange(WINDOW, n_steps - max_h, stride)
    X, Y, T, S = [], [], [], []
    for t in times:
        X.append(tokens[t - WINDOW:t].transpose(1, 0, 2))      # (stocks, W, F)
        Y.append(np.stack([cum[t + h] - cum[t] for h in AUX_HORIZONS], axis=-1))
        T.append(np.full(n_stocks, t))
        S.append(np.arange(n_stocks))
    X = np.concatenate(X)
    Y = np.concatenate(Y)
    T = np.concatenate(T)
    S = np.concatenate(S)
    return X, Y, T, S, regime[T]


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------
def rankdata(a):
    r = np.empty(len(a))
    r[np.argsort(a, kind='mergesort')] = np.arange(len(a))
    return r


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    ra -= ra.mean()
    rb -= rb.mean()
    den = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / den) if den > 0 else 0.0


def rank_ic(pred, target, times):
    """Mean cross-sectional Spearman correlation over timestamps."""
    ics = [spearman(pred[times == t], target[times == t]) for t in np.unique(times)]
    return float(np.mean(ics))


def effective_dim(Z):
    """Participation ratio of the embedding covariance spectrum."""
    ev = np.clip(np.linalg.eigvalsh(np.cov(Z, rowvar=False)), 0, None)
    return float(ev.sum() ** 2 / (ev ** 2).sum())


# --------------------------------------------------------------------------
# linear probe
# --------------------------------------------------------------------------
class Ridge:
    def __init__(self, alpha=1.0):
        self.alpha = alpha

    def fit(self, X, y):
        self.mu = X.mean(0)
        self.sd = X.std(0) + 1e-8
        Xs = (X - self.mu) / self.sd
        self.y_mu = y.mean(0)
        A = Xs.T @ Xs + self.alpha * len(Xs) * np.eye(X.shape[1])
        self.w = np.linalg.solve(A, Xs.T @ (y - self.y_mu))
        return self

    def predict(self, X):
        return ((X - self.mu) / self.sd) @ self.w + self.y_mu


def sector_probe_acc(Z_tr, s_tr, Z_te, s_te, n_sectors):
    """How much company structure survives: ridge one-vs-rest sector probe."""
    probe = Ridge(1e-3).fit(Z_tr, np.eye(n_sectors)[s_tr])
    return float((probe.predict(Z_te).argmax(1) == s_te).mean())


# --------------------------------------------------------------------------
# encoders (all map (N, W, F) -> (N, D) and are frozen before probing)
# --------------------------------------------------------------------------
class Last24:
    name = 'ridge_last24'

    def fit(self, X, Y, rng):
        return self

    def encode(self, X):
        return X[:, -24:].reshape(len(X), -1)


class RandomEncoder:
    """Untrained network: random projection of the full window + tanh."""
    name = 'random_encoder'

    def __init__(self, dim=128):
        self.dim = dim

    def fit(self, X, Y, rng):
        d_in = X.shape[1] * X.shape[2]
        self.W = rng.standard_normal((d_in, self.dim)) / np.sqrt(d_in)
        self.b = rng.uniform(-0.5, 0.5, self.dim)
        return self

    def encode(self, X):
        return np.tanh(X.reshape(len(X), -1) @ self.W + self.b)


class PCAEncoder:
    """Self-supervised by reconstruction: top principal components of windows."""
    name = 'pca_ssl'

    def __init__(self, dim=32):
        self.dim = dim

    def fit(self, X, Y, rng):
        F = X.reshape(len(X), -1)
        self.mu = F.mean(0)
        _, _, vt = np.linalg.svd(F[rng.choice(len(F), min(len(F), 20000), replace=False)]
                                 - self.mu, full_matrices=False)
        self.P = vt[:self.dim].T
        return self

    def encode(self, X):
        return (X.reshape(len(X), -1) - self.mu) @ self.P


class MLPEncoder:
    """Two-layer MLP trained with Adam on forward returns; hidden layer = state."""

    def __init__(self, heads, dim=64, epochs=6, lr=1e-3, batch=512):
        self.heads = list(heads)
        self.dim, self.epochs, self.lr, self.batch = dim, epochs, lr, batch
        self.name = 'supervised' if len(self.heads) == 1 else 'multi_head'

    def _forward(self, F):
        h1 = np.maximum(F @ self.W1 + self.b1, 0)
        z = np.tanh(h1 @ self.W2 + self.b2)
        return h1, z

    def fit(self, X, Y, rng):
        F = X.reshape(len(X), -1)
        Yh = Y[:, self.heads]
        Yh = (Yh - Yh.mean(0)) / (Yh.std(0) + 1e-12)
        d_in, hid = F.shape[1], 128
        params = {
            'W1': rng.standard_normal((d_in, hid)) * np.sqrt(2 / d_in), 'b1': np.zeros(hid),
            'W2': rng.standard_normal((hid, self.dim)) / np.sqrt(hid), 'b2': np.zeros(self.dim),
            'W3': rng.standard_normal((self.dim, Yh.shape[1])) * 0.01, 'b3': np.zeros(Yh.shape[1]),
        }
        m = {k: np.zeros_like(v) for k, v in params.items()}
        v = {k: np.zeros_like(p) for k, p in params.items()}
        step = 0
        for _ in range(self.epochs):
            for idx in np.array_split(rng.permutation(len(F)), max(1, len(F) // self.batch)):
                for k, p in params.items():
                    setattr(self, k, p)
                xb, yb = F[idx], Yh[idx]
                h1, z = self._forward(xb)
                err = (z @ self.W3 + self.b3 - yb) / len(idx)
                dz = (err @ self.W3.T) * (1 - z ** 2)
                dh1 = (dz @ self.W2.T) * (h1 > 0)
                grads = {'W3': z.T @ err, 'b3': err.sum(0),
                         'W2': h1.T @ dz, 'b2': dz.sum(0),
                         'W1': xb.T @ dh1, 'b1': dh1.sum(0)}
                step += 1
                for k, g in grads.items():
                    m[k] = 0.9 * m[k] + 0.1 * g
                    v[k] = 0.999 * v[k] + 0.001 * g ** 2
                    mh = m[k] / (1 - 0.9 ** step)
                    vh = v[k] / (1 - 0.999 ** step)
                    params[k] -= self.lr * mh / (np.sqrt(vh) + 1e-8)
        for k, p in params.items():
            setattr(self, k, p)
        return self

    def encode(self, X):
        return self._forward(X.reshape(len(X), -1))[1]


# --------------------------------------------------------------------------
# experiment
# --------------------------------------------------------------------------
def run(args):
    rng = np.random.default_rng(args.seed)
    returns, volume, sector, regime = simulate_market(
        args.stocks, args.steps, args.regimes, args.sectors, rng)
    tokens = make_tokens(returns, volume)
    X, Y, T, S, R = build_samples(tokens, returns, regime, args.stride)

    # first half of every regime trains, second half tests: every encoder is
    # evaluated on all regimes, as in the paper's 32-regime protocol
    split = np.zeros(len(T), dtype=bool)
    for r in np.unique(R):
        ts = np.unique(T[R == r])
        split |= (R == r) & (T >= ts[len(ts) // 2])
    tr, te = ~split, split
    target = AUX_HORIZONS.index(HORIZON)
    logger.info('samples: train %d, test %d, token dim %s', tr.sum(), te.sum(), X.shape[1:])

    encoders = [
        Last24(),
        RandomEncoder(),
        PCAEncoder(),
        MLPEncoder(heads=[target], epochs=args.epochs),
        MLPEncoder(heads=range(len(AUX_HORIZONS)), epochs=args.epochs),
    ]

    results = []
    for enc in encoders:
        enc.fit(X[tr], Y[tr], np.random.default_rng(args.seed + 1))
        Z_tr, Z_te = enc.encode(X[tr]), enc.encode(X[te])
        probe = Ridge(args.alpha).fit(Z_tr, Y[tr, target])
        pred = probe.predict(Z_te)
        y_te, t_te, r_te = Y[te, target], T[te], R[te]
        per_regime = [rank_ic(pred[r_te == r], y_te[r_te == r], t_te[r_te == r])
                      for r in np.unique(r_te)]
        results.append({
            'name': enc.name,
            'ic': rank_ic(pred, y_te, t_te),
            'ic_regimes': per_regime,
            'eff_dim': effective_dim(Z_te),
            'sector_acc': sector_probe_acc(Z_tr, sector[S[tr]], Z_te, sector[S[te]], args.sectors),
        })
    return results


def report(results, n_sectors):
    print('\n%-16s %9s %10s %8s %10s' % ('encoder', 'rank IC', 'IC>0 reg', 'eff.dim', 'sector acc'))
    for r in sorted(results, key=lambda r: -r['ic']):
        wins = np.mean(np.array(r['ic_regimes']) > 0)
        print('%-16s %9.4f %9.0f%% %8.1f %10.2f' % (
            r['name'], r['ic'], 100 * wins, r['eff_dim'], r['sector_acc']))
    print('(sector chance level: %.2f)' % (1 / n_sectors))
    ic = [r['ic'] for r in results]
    print('Spearman(rank IC, eff.dim)    = %+.2f' % spearman(ic, [r['eff_dim'] for r in results]))
    print('Spearman(rank IC, sector acc) = %+.2f' % spearman(ic, [r['sector_acc'] for r in results]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--stocks', type=int, default=60)
    parser.add_argument('--steps', type=int, default=6000)
    parser.add_argument('--regimes', type=int, default=8)
    parser.add_argument('--sectors', type=int, default=6)
    parser.add_argument('--stride', type=int, default=5, help='step between sample windows')
    parser.add_argument('--epochs', type=int, default=6)
    parser.add_argument('--alpha', type=float, default=1e-2, help='ridge probe penalty')
    parser.add_argument('--seed', type=int, default=0)
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    report(run(parser.parse_args()), parser.parse_args().sectors)
