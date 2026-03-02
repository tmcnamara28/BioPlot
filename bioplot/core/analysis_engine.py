"""Stateless analysis functions: DEG, PCA, normalization.

All functions are pure (no side effects, no Qt imports) and testable headlessly.
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pandas as pd


# ── Normalization ─────────────────────────────────────────────────────────────

def cpm_normalize(counts: pd.DataFrame) -> pd.DataFrame:
    """Counts Per Million normalization."""
    total = counts.sum(axis=0)
    return counts.divide(total, axis=1) * 1e6


def log1p_normalize(counts: pd.DataFrame, base: float = 2.0) -> pd.DataFrame:
    """log1p normalization with configurable base."""
    import numpy as np
    normed = cpm_normalize(counts)
    if base == np.e:
        return np.log1p(normed)
    return np.log1p(normed) / np.log(base)


# ── Differential Expression ───────────────────────────────────────────────────

def run_deg(
    counts: pd.DataFrame,
    group_a: list[str],
    group_b: list[str],
    method: str = "ttest",
    correction: str = "fdr_bh",
    log_transform: bool = True,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> pd.DataFrame:
    """Run differential expression analysis between two sample groups.

    Parameters
    ----------
    counts:
        Raw counts DataFrame (genes × samples).
    group_a, group_b:
        Column names in ``counts`` for each condition.
    method:
        Statistical test: ``"ttest"`` (Student) or ``"wilcoxon"``.
    correction:
        Multiple-testing correction method for ``statsmodels.stats.multitest``.
    log_transform:
        Whether to log1p-normalize before testing.
    progress_callback:
        Optional callable receiving int 0–100.

    Returns
    -------
    DataFrame with columns: gene, log2FC, pvalue, padj, mean_a, mean_b.
    """
    from scipy import stats as sp_stats
    from statsmodels.stats.multitest import multipletests

    data = log1p_normalize(counts) if log_transform else counts.astype(float)

    a = data[group_a]
    b = data[group_b]

    genes = list(counts.index)
    n = len(genes)
    pvals = np.empty(n)
    log2fc = np.empty(n)
    mean_a = a.mean(axis=1).values
    mean_b = b.mean(axis=1).values

    if progress_callback:
        progress_callback(10)

    for i, gene in enumerate(genes):
        va = a.loc[gene].values.astype(float)
        vb = b.loc[gene].values.astype(float)
        if method == "wilcoxon":
            try:
                _, pvals[i] = sp_stats.mannwhitneyu(va, vb, alternative="two-sided")
            except ValueError:
                pvals[i] = 1.0
        else:
            _, pvals[i] = sp_stats.ttest_ind(va, vb, equal_var=False)

        denom = mean_b[i] if mean_b[i] != 0 else 1e-10
        log2fc[i] = np.log2((mean_a[i] + 1e-10) / (denom + 1e-10))

        if progress_callback and i % max(1, n // 20) == 0:
            progress_callback(10 + int(80 * i / n))

    # Handle NaN p-values
    pvals = np.nan_to_num(pvals, nan=1.0)

    _, padj, _, _ = multipletests(pvals, method=correction)

    if progress_callback:
        progress_callback(95)

    result = pd.DataFrame(
        {
            "gene": genes,
            "log2FC": log2fc,
            "pvalue": pvals,
            "padj": padj,
            "mean_A": mean_a,
            "mean_B": mean_b,
            "neg_log10_padj": -np.log10(padj + 1e-300),
        }
    ).set_index("gene")

    return result


# ── PCA ───────────────────────────────────────────────────────────────────────

def run_pca(
    counts: pd.DataFrame,
    n_components: int = 10,
    log_transform: bool = True,
    scale: bool = True,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run PCA on expression matrix.

    Parameters
    ----------
    counts:
        Genes × samples DataFrame.
    n_components:
        Number of principal components.
    log_transform:
        Log1p-normalize before PCA.
    scale:
        z-score scale each gene before PCA.

    Returns
    -------
    coords : (n_samples, n_components) array
    explained_variance_ratio : (n_components,) array
    loadings : (n_genes, n_components) array
    """
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    data = log1p_normalize(counts) if log_transform else counts.astype(float)

    # PCA expects samples as rows
    X = data.T.values  # (n_samples, n_genes)

    if progress_callback:
        progress_callback(20)

    if scale:
        scaler = StandardScaler()
        X = scaler.fit_transform(X)

    if progress_callback:
        progress_callback(40)

    n_comp = min(n_components, X.shape[0] - 1, X.shape[1])
    pca = PCA(n_components=n_comp)
    coords = pca.fit_transform(X)

    if progress_callback:
        progress_callback(90)

    return coords, pca.explained_variance_ratio_, pca.components_.T
