"""Unit tests for stateless analysis functions."""
import numpy as np
import pandas as pd
import pytest

from bioplot.core.analysis_engine import (
    cpm_normalize, log1p_normalize, run_deg, run_pca,
)


@pytest.fixture
def counts_df():
    rng = np.random.default_rng(42)
    n_genes = 100
    n_samples = 10
    data = rng.negative_binomial(20, 0.5, (n_genes, n_samples)).astype(float)
    genes = [f"Gene{i:03d}" for i in range(n_genes)]
    samples = [f"Sample{i}" for i in range(n_samples)]
    return pd.DataFrame(data, index=genes, columns=samples)


class TestNormalization:
    def test_cpm_col_sum(self, counts_df):
        normed = cpm_normalize(counts_df)
        col_sums = normed.sum(axis=0)
        assert (np.abs(col_sums - 1e6) < 1.0).all(), "CPM columns should sum to 1e6"

    def test_log1p_nonneg(self, counts_df):
        normed = log1p_normalize(counts_df)
        assert (normed >= 0).all().all()

    def test_shapes_preserved(self, counts_df):
        normed = cpm_normalize(counts_df)
        assert normed.shape == counts_df.shape


class TestDEG:
    def test_deg_output_shape(self, counts_df):
        group_a = ["Sample0", "Sample1", "Sample2", "Sample3", "Sample4"]
        group_b = ["Sample5", "Sample6", "Sample7", "Sample8", "Sample9"]
        result = run_deg(counts_df, group_a, group_b)

        assert "log2FC" in result.columns
        assert "pvalue" in result.columns
        assert "padj" in result.columns
        assert len(result) == 100

    def test_pvalue_range(self, counts_df):
        group_a = ["Sample0", "Sample1", "Sample2", "Sample3", "Sample4"]
        group_b = ["Sample5", "Sample6", "Sample7", "Sample8", "Sample9"]
        result = run_deg(counts_df, group_a, group_b)
        assert (result["pvalue"] >= 0).all()
        assert (result["pvalue"] <= 1).all()
        assert (result["padj"] >= 0).all()
        assert (result["padj"] <= 1).all()

    def test_padj_gte_pvalue(self, counts_df):
        """BH-corrected p-values should be >= raw p-values."""
        group_a = ["Sample0", "Sample1", "Sample2", "Sample3", "Sample4"]
        group_b = ["Sample5", "Sample6", "Sample7", "Sample8", "Sample9"]
        result = run_deg(counts_df, group_a, group_b)
        assert (result["padj"] >= result["pvalue"] - 1e-10).all()

    def test_wilcoxon_method(self, counts_df):
        group_a = ["Sample0", "Sample1", "Sample2", "Sample3", "Sample4"]
        group_b = ["Sample5", "Sample6", "Sample7", "Sample8", "Sample9"]
        result = run_deg(counts_df, group_a, group_b, method="wilcoxon")
        assert len(result) == 100

    def test_simulated_degs_detected(self):
        """Artificially inflated genes should be detected as significant."""
        rng = np.random.default_rng(0)
        n_genes = 50
        data = {f"A{i}": rng.poisson(10, n_genes).astype(float) for i in range(5)}
        data.update({f"B{i}": rng.poisson(10, n_genes).astype(float) for i in range(5)})

        df = pd.DataFrame(data, index=[f"G{i}" for i in range(n_genes)])
        # Make first 5 genes clearly DE
        for col in [f"B{i}" for i in range(5)]:
            df.loc["G0", col] = 200.0
            df.loc["G1", col] = 200.0
            df.loc["G2", col] = 200.0

        group_a = [f"A{i}" for i in range(5)]
        group_b = [f"B{i}" for i in range(5)]
        result = run_deg(df, group_a, group_b)

        sig = result[result["padj"] < 0.05]
        # At least some of the planted DE genes should be detected
        assert len(sig) >= 1


class TestPCA:
    def test_output_shapes(self, counts_df):
        coords, evr, loadings = run_pca(counts_df, n_components=5)
        assert coords.shape[0] == 10    # n_samples
        assert coords.shape[1] == 5    # n_components
        assert evr.shape[0] == 5
        assert loadings.shape[1] == 5  # (n_genes, n_components)

    def test_evr_sum_lte_1(self, counts_df):
        _, evr, _ = run_pca(counts_df)
        assert evr.sum() <= 1.0 + 1e-9

    def test_evr_decreasing(self, counts_df):
        _, evr, _ = run_pca(counts_df)
        assert all(evr[i] >= evr[i + 1] for i in range(len(evr) - 1))
