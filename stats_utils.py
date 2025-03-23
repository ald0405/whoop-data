from math import sqrt
from scipy.stats import norm
from typing import Tuple
from scipy.stats import ttest_ind
import numpy as np 
import seaborn as sns
import matplotlib.pyplot as plt 


class IndependentGroupsAnalysis:
    """
    Analyse the difference between two independent groups.

    This class performs:
    - Welch's T-Test for hypothesis testing
    - Cohen's D for effect size estimation
    - Histogram plotting to visualize group differences
    """

    def __init__(self):
        pass

    def load_data(self, 
                  group_a: np.ndarray, 
                  group_b: np.ndarray, 
                  alpha: float = 0.05
                  ) -> None:
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

    def _cohen_d(self) -> None:
        """
        Compute Cohen's d effect size between the two groups.
        """
        self.mean_difference = self.mean_a - self.mean_b
        self.group_a_var = np.var(self.group_a, ddof=1)
        self.group_b_var = np.var(self.group_b, ddof=1)
        self.pooled_std = np.sqrt((self.group_a_var + self.group_b_var) / 2)
        self.cohen_d_effect_size = round(self.mean_difference / self.pooled_std, 3)

    def _welch_t_test(self) -> None: 
        """
        Perform Welch's t-test and compute Cohen's d.
        """
        self.t_stat, self.p_value = ttest_ind(
            self.group_a,
            self.group_b,
            equal_var=False,
            alternative="two-sided"
        )

    def test_groups(self) -> None:
        self._welch_t_test()
        self._cohen_d()

    def summarise(self) -> None:
        """
        Print a summary of the t-test and effect size results.
        """
        print("=" * 60)
        print(f"Group A mean: {self.mean_a:.3f} | Group B mean: {self.mean_b:.3f}")
        print(f"t-statistic: {self.t_stat:.3f}")
        print(f"p-value: {self.p_value:.3g}")
        print(f"Cohen's d (effect size): {self.cohen_d_effect_size}")
        if self.p_value < self.alpha:
            print("✅ Statistically significant difference between groups.")
        else:
            print("❌ No statistically significant difference between groups.")
        print("=" * 60)

    def describe(self) -> None:
        """
        Print basic descriptive statistics for both groups.
        """
        from scipy.stats import skew, kurtosis

        print("Descriptive Statistics:\n" + "=" * 60)
        for label, group in zip(["Group A", "Group B"], [self.group_a, self.group_b]):
            print(f"{label}:")
            print(f"  Min      : {min(group):.3f}")
            print(f"  Max      : {max(group):.3f}")
            print(f"Samples    : {len(group):.3f}")
            print(f"  Mean     : {np.mean(group):.3f}")
            print(f"  Median   : {np.median(group):.3f}")
            print(f"  Std Dev  : {np.std(group, ddof=1):.3f}")
            print(f"  Skew     : {skew(group):.3f}")
            print(f"  Kurtosis : {kurtosis(group):.3f}")
            print("-" * 60)

    def results(self) -> dict:
        """
        Return a dictionary of the statistical test results.

        Returns:
        - dict with t_statistic, p_value, cohen_d, mean_group_a, mean_group_b
        """
        return {
            "t_statistic": self.t_stat,
            "p_value": self.p_value,
            "cohen_d": self.cohen_d_effect_size,
            "mean_group_a": self.mean_a,
            "mean_group_b": self.mean_b
        }

    def plot_distributions(self, 
                           label_a="Group A", 
                           label_b="Group B", 
                           xlabel="Value",
                           title="Distribution of Values by Category (t-test)") -> None:
        """
        Plot histogram of the distributions for both groups.

        Parameters:
        - label_a: str - Label for group A
        - label_b: str - Label for group B
        - xlabel: str - X-axis label
        - title: str - Plot title
        """
        sns.set_theme(style='whitegrid')
        # plt.rcParams.update(plot_config.plot_style)

        fig, ax = plt.subplots(figsize=(9, 6))

        ax.hist(
            self.group_a,
            edgecolor='white',
            alpha=0.8,
            label=label_a,
            bins= int(np.sqrt(len(self.group_a)))
        )
        ax.hist(
            self.group_b,
            edgecolor='white',
            alpha=0.4,
            label=label_b,
            bins= int(np.sqrt(len(self.group_b)))
        )

        ax.text(
            0.02, 0.95,
            f"p-value: {self.p_value:.3f}\nt-value: {self.t_stat:.3f}\nEffect Size d = {self.cohen_d_effect_size}",
            transform=ax.transAxes,
            fontsize=12,
            fontweight='bold',
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='grey', alpha=0.6)
        )

        ax.set_title(title, fontsize=14, weight='bold')
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.legend(title='Group')
    
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

    def confidence_intervals(self, 
                             confidence: float, 
                             sample_mean: float, 
                             sample_std: float, 
                             n: int
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
    def compute(cls, 
                confidence: float, 
                sample_mean: float, 
                sample_std: float, 
                n: int
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
