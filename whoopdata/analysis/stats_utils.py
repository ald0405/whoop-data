import numpy as np

# Configure matplotlib for headless operation before importing pyplot
import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

plt.ioff()  # Turn off interactive mode
import seaborn as sns
from math import sqrt
from scipy.stats import norm
from typing import Tuple
from scipy.stats import ttest_ind, mannwhitneyu
from colorama import Fore, Style, init
from scipy.stats import skew, kurtosis

init(autoreset=True)


class IndependentGroupsAnalysis:
    """
    Analyse the difference between two independent groups.

     This class performs:
    - Welch's T-Test or Mann-Whitney U Test for hypothesis testing
      (Welch's assumes normality and unequal variance; Mann-Whitney is non-parametric)
    - Cohen's d or Cliff's Delta for effect size estimation
    - Histogram plotting to visualize group differences

    Interpretation:
    - Cohen's d: Measures how many standard deviations apart the group means are.
      (0.2 = small, 0.5 = medium, 0.8 = large effect)
    - Cliff's Delta: Measures the probability that one group will have higher values than another.
      (0.1 = small, 0.3 = medium, 0.5+ = large effect)
    """

    def __init__(self):
        pass

    def load_data(self, group_a: np.ndarray, group_b: np.ndarray, alpha: float = 0.05) -> None:
        """
        Load the data for both groups and define the significance level.

        Parameters:
        - group_a: np.ndarray - Data for group A
        - group_b: np.ndarray - Data for group B
        - alpha: float - Significance level for the hypothesis test (default 0.05)
        """
        self.group_a = np.array(group_a)
        self.group_b = np.array(group_b)
        self.alpha = alpha
        self.mean_a = np.mean(self.group_a)
        self.mean_b = np.mean(self.group_b)
        self.median_a = np.median(self.group_a)
        self.median_b = np.median(self.group_b)

    def _manwhitney(self):
        """
        Perform the Mann-Whitney U test, a non-parametric alternative to the t-test.
        Stores U-statistic and p-value.
        """
        self.mu_U, self.p_value = mannwhitneyu(self.group_a, self.group_b, alternative="two-sided")

    def _cliffs_delta(self) -> None:
        """
        Fast Cliff's Delta using NumPy broadcasting (O(n log n)).
        Compute Cliff's Delta effect size, a non-parametric alternative to Cohen's d.
        It measures the probability that one group tends to have larger values than the other.

        """
        a = self.group_a
        b = self.group_b
        n = len(a) * len(b)

        # Use numpy broadcasting to speed up comparisons
        diff_matrix = np.subtract.outer(a, b)
        greater = np.sum(diff_matrix > 0)
        less = np.sum(diff_matrix < 0)

        self.cliff_delta_effect_size = (greater - less) / n

    def _welch_t_test(self) -> None:
        """
        Perform Welch's t-test (for unequal variances) on the two groups.
        Stores t-statistic and p-value.
        """
        self.t_stat, self.p_value = ttest_ind(
            self.group_a, self.group_b, equal_var=False, alternative="two-sided"
        )

    def _cohen_d(self) -> None:
        """
        Perform Welch's t-test (for unequal variances) on the two groups.
        Stores t-statistic and p-value.
        """
        self.mean_difference = self.mean_a - self.mean_b
        self.group_a_var = np.var(self.group_a, ddof=1)
        self.group_b_var = np.var(self.group_b, ddof=1)
        self.pooled_std = np.sqrt((self.group_a_var + self.group_b_var) / 2)
        self.cohen_d_effect_size = round(self.mean_difference / self.pooled_std, 3)

    def test_groups(self) -> None:
        """
        Run Welch's t-test and compute Cohen's d.
        """
        self._welch_t_test()
        self._cohen_d()

    def test_non_parametric_groups(self) -> None:
        """
        Run Mann-Whitney U test and compute Cliff's Delta.
        """
        self._manwhitney()
        self._cliffs_delta()

    def summarise_mu(self) -> None:
        print(self.p_value, self.mu_U)

    def summarise(self) -> None:
        """
        Print a summary of the t-test and effect size results.
        """
        print("=" * 60)
        print(f"Group A mean: {self.mean_a:.3f} | Group B mean: {self.mean_b:.3f}")
        if hasattr(self, "t_stat") and self.t_stat is not None:
            print(f"t-statistic: {self.t_stat:.3f}")
        else:
            print(f"U-statistic: {self.mu_U:.3f}")

        if hasattr(self, "cohen_d_effect_size") and self.cohen_d_effect_size is not None:
            print(f"Cohen's d (effect size): {self.cohen_d_effect_size}")
        else:
            print(f"Cliff's Delta (effect size): {self.cliff_delta_effect_size}")

        if self.p_value < self.alpha:
            print(Fore.GREEN + "✅ Statistically significant difference between groups.")
        else:
            print(Fore.RED + "❌ No statistically significant difference between groups.")
        print("=" * 60)

    def describe(self) -> str:
        """
        Print basic descriptive statistics for both groups.
        """
        from scipy.stats import skew, kurtosis

        print("Descriptive Statistics:\n" + "=" * 60)
        for label, group in zip(["Group A", "Group B"], [self.group_a, self.group_b]):
            print(Fore.MAGENTA + f"{label}:")
            print(Fore.MAGENTA + f"  Min      : {min(group):.3f}")
            print(Fore.MAGENTA + f"  Max      : {max(group):.3f}")
            print(Fore.MAGENTA + f"  n        : {len(group):.3f}")
            print(Fore.MAGENTA + f"  Mean     : {np.mean(group):.3f}")
            print(Fore.MAGENTA + f"  Median   : {np.median(group):.3f}")
            print(Fore.MAGENTA + f"  Std Dev  : {np.std(group, ddof=1):.3f}")
            print(Fore.MAGENTA + f"  Skew     : {skew(group):.3f}")
            print(Fore.MAGENTA + f"  Kurtosis : {kurtosis(group):.3f}")
            print("-" * 60)

    @staticmethod
    def _interpret_cohens_d(d: float) -> str:
        d = abs(d)
        if d < 0.2:
            return "negligible"
        elif d < 0.5:
            return "small"
        elif d < 0.8:
            return "medium"
        else:
            return "large"

    @staticmethod
    def _interpret_cliffs_delta(delta: float) -> str:
        delta = abs(delta)
        if delta < 0.147:
            return "negligible"
        elif delta < 0.33:
            return "small"
        elif delta < 0.474:
            return "medium"
        else:
            return "large"

    def results(self) -> dict:
        """
        Return a JSON-friendly dictionary of all relevant statistical test results.
        Suitable for passing to an LLM for further explanation or display.
        """

        results = {
            "test_type": "Welch's t-test" if hasattr(self, "t_stat") else "Mann-Whitney U",
            "alpha": self.alpha,
            "p_value": self.p_value,
            "significant": self.p_value < self.alpha,
            "group_a": {
                "label": "Group A",
                "n": len(self.group_a),
                "mean": float(np.mean(self.group_a)),
                "median": float(np.median(self.group_a)),
                "std": float(np.std(self.group_a, ddof=1)),
                "skew": float(skew(self.group_a)),
                "kurtosis": float(kurtosis(self.group_a)),
            },
            "group_b": {
                "label": "Group B",
                "n": len(self.group_b),
                "mean": float(np.mean(self.group_b)),
                "median": float(np.median(self.group_b)),
                "std": float(np.std(self.group_b, ddof=1)),
                "skew": float(skew(self.group_b)),
                "kurtosis": float(kurtosis(self.group_b)),
            },
        }

        # Test statistic and effect size
        if hasattr(self, "t_stat"):
            results["statistic"] = {
                "t_statistic": float(self.t_stat),
                "effect_size": {
                    "type": "Cohen's d",
                    "value": float(self.cohen_d_effect_size),
                    "interpretation": self._interpret_cohens_d(self.cohen_d_effect_size),
                },
            }
        else:
            results["statistic"] = {
                "mannwhitney_u": float(self.mu_U),
                "effect_size": {
                    "type": "Cliff's Delta",
                    "value": float(self.cliff_delta_effect_size),
                    "interpretation": self._interpret_cliffs_delta(self.cliff_delta_effect_size),
                },
            }

        return results

    def results_mu(self) -> dict:
        """
        Returns a dictionary of the statistical test

        Returns:
        - dict with U statistic, p_value, cliff's delta,median_group_a, median_group_b
        """
        return {
            "mannwhitney_u": self.mu_U,
            "p_value": self.p_value,
            "cliffs_delta": self.cliff_delta_effect_size,
            "median_group_b": self.median_a,
            "median_group_b": self.median_b,
        }

    def plot_distributions(
        self,
        label_a="Group A",
        label_b="Group B",
        xlabel="Value",
        title="Distribution of Values by Category (t-test)",
    ) -> None:
        """
        Plot histogram of the distributions for both groups.

        Parameters:
        - label_a: str - Label for group A
        - label_b: str - Label for group B
        - xlabel: str - X-axis label
        - title: str - Plot title
        """
        sns.set_theme(style="whitegrid")

        fig, ax = plt.subplots(figsize=(9, 6))

        ax.hist(
            self.group_a,
            edgecolor="white",
            alpha=0.8,
            label=label_a,
            bins=int(np.sqrt(len(self.group_a) + len(self.group_b))),
        )
        ax.hist(
            self.group_b,
            edgecolor="white",
            alpha=0.4,
            label=label_b,
            bins=int(np.sqrt(len(self.group_a) + len(self.group_b))),
        )

        if hasattr(self, "cohen_d_effect_size"):
            stat_label = f"t-value: {self.t_stat:.3f}"
            effect_label = f"Effect Size d = {self.cohen_d_effect_size}"
        else:
            stat_label = f"U-statistic: {self.mu_U:.3f}"
            effect_label = f"Cliff's Delta = {self.cliff_delta_effect_size}"

        ax.text(
            0.02,
            0.95,
            f"p-value: {self.p_value:.3f}\n" f"{stat_label}\n" f"{effect_label}",
            transform=ax.transAxes,
            fontsize=12,
            fontweight="bold",
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="grey", alpha=0.6),
        )

        ax.set_title(title, fontsize=14, weight="bold")
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.legend(title="Group")

        sns.despine()

        plt.tight_layout()
        plt.show()


class SampleCertainty:
    """
    A utility class for computing confidence intervals using the normal distribution.
    Use outputs for `IndependentGroupsAnalysis` which will provide summary statisics
    """

    def __init__(self):
        pass

    def critical_z_value(self, confidence: float) -> Tuple[float, float]:
        """
        Calculate the critical z-values for a given confidence level.

        Parameters:
        - confidence: float - Confidence level (e.g., 0.95 for 95%)

        Returns:
        - Tuple containing the lower and upper z critical values
        """
        norm_dist = norm(loc=0.0, scale=1.0)
        left_tail_area = (1.0 - confidence) / 2.0
        upper_area = 1.0 - left_tail_area
        return norm_dist.ppf(left_tail_area), norm_dist.ppf(upper_area)

    def confidence_intervals(
        self, confidence: float, sample_mean: float, sample_std: float, n: int
    ) -> Tuple[float, float]:
        """
        Compute a two-sided confidence interval for the mean using the normal distribution.

        Parameters:
        - confidence: float - Confidence level (e.g., 0.95 for 95%)
        - sample_mean: float - Sample mean
        - sample_std: float - Sample standard deviation
        - n: int - Sample size

        Returns:
        - Tuple of (lower_bound, upper_bound)
        """
        lower, upper = self.critical_z_value(confidence)
        margin_error_lower = lower * (sample_std / sqrt(n))
        margin_error_upper = upper * (sample_std / sqrt(n))
        return sample_mean + margin_error_lower, sample_mean + margin_error_upper

    @classmethod
    def compute(
        cls, confidence: float, sample_mean: float, sample_std: float, n: int
    ) -> Tuple[float, float]:
        """
        Compute confidence interval in a one-liner using the class directly.

        Parameters:
        - confidence: float - Confidence level (e.g., 0.95 for 95%)
        - sample_mean: float - Sample mean
        - sample_std: float - Sample standard deviation
        - n: int - Sample size

        Returns:
        - Tuple of (lower_bound, upper_bound)
        """
        instance = cls()
        return instance.confidence_intervals(confidence, sample_mean, sample_std, n)
