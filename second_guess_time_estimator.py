import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tabulate import tabulate
import expected_value as ev

def estimate_runtime(max_sample_size=20, runs_per_size=3):
    """
    Estimates runtime for the full analysis function by running small samples
    and extrapolating to larger sizes.
    
    Args:
        max_sample_size: Maximum number of candidates to test with
        runs_per_size: Number of times to run each test for more accurate timing
    
    Returns:
        Formula coefficients and projected runtimes for different candidate counts
    """
    # Sample words from the word list
    print("Loading word list...")
    word_list = pd.read_csv("word_list.csv")
    sample_words = word_list["WORD"].sample(max_sample_size).values
    
    # Test with increasing numbers of candidates
    #sizes = [2, 4, 6, 8, 10, 15, max_sample_size]

    # Generate better distributed test sizes
    # Always include very small sizes for baseline
    small_sizes = [1,2, 5,8, 10]
    
    # Add intermediate sizes based on max_sample_size
    if max_sample_size <= 20:
        # For small max sizes, use closer intervals
        med_sizes = list(range(12, max_sample_size, 2))
    elif max_sample_size <= 50:
        # For medium max sizes, use wider spacing
        med_sizes = [15, 20, 25, 30, 40]
    else:
        # For larger max sizes, use logarithmic-like spacing
        med_sizes = [15, 20, 30, 40, 60, 80]
    
    # Always include the max size
    sizes = small_sizes + [s for s in med_sizes if s < max_sample_size] + [max_sample_size]
    
    # Remove duplicates and sort
    sizes = sorted(list(set(sizes)))

    sizes = [s for s in sizes if s <= max_sample_size]
    times = []
    
    print(f"Running tests with candidate sizes: {sizes}")
    for size in sizes:
        candidates = sample_words[:size]
        candidates_df = pd.DataFrame({"WORD": candidates})
        
        # Run multiple times for stability
        total_time = 0
        print(f"Testing {size} candidates... ", end="", flush=True)
        
        for run in range(runs_per_size):
            start = time.time()
            ev.perform_full_analysis(candidates, candidates_df)
            end = time.time()
            run_time = end - start
            total_time += run_time
            print(f"run {run+1}: {run_time:.4f}s", end=" | " if run < runs_per_size-1 else "\n", flush=True)
        
        avg_time = total_time / runs_per_size
        times.append(avg_time)
        print(f"Average: {avg_time:.4f} seconds")
    
    # Fit quadratic curve (O(n²) behavior)
    X = np.vstack([np.array(sizes)**2, np.array(sizes), np.ones(len(sizes))]).T
    coeffs = np.linalg.lstsq(X, times, rcond=None)[0]
    a, b, c = coeffs
    
    # Generate a clear rule for estimation
    rule = f"Time (seconds) = {a:.8f} × n² + {b:.8f} × n + {c:.8f}"
    simplified_rule = f"Time (seconds) ~= {a:.8f} × n²"
    if abs(b) > 0.001:
        simplified_rule += f" + {b:.4f} × n"
    if abs(c) > 0.01:
        simplified_rule += f" + {c:.4f}"
    
    print("\n=== GENERAL ESTIMATION RULE ===")
    print(rule)
    print(f"Simplified: {simplified_rule}")
    print("Where n is the number of candidates for a pattern")
    
    # Function to estimate time for any number of candidates
    def estimate_time(n):
        return a * n**2 + b * n + c
    
    # Generate time estimate table
    table_sizes = [1, 5, 10, 25, 50, 100, 250, 500, 1000]
    
    table_data = []
    for size in table_sizes:
        est_seconds = estimate_time(size)
        
        # Format time in appropriate units
        if est_seconds < 60:
            time_str = f"{est_seconds:.2f} seconds"
        elif est_seconds < 3600:
            time_str = f"{est_seconds/60:.2f} minutes"
        else:
            time_str = f"{est_seconds/3600:.2f} hours"
        
        table_data.append([size, est_seconds, time_str])
    
    # Display the table
    print("\n=== ESTIMATED RUNTIME BY CANDIDATE COUNT ===")
    headers = ["Candidates", "Seconds", "Human-readable"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Save table to file for easier reference
    with open("runtime_estimates.txt", "w", encoding="utf-8") as f:
        f.write("=== RUNTIME ESTIMATION FOR PATTERNS ===\n\n")
        f.write(f"Formula: {rule}\n")
        f.write(f"Simplified: {simplified_rule}\n\n")
        f.write(tabulate(table_data, headers=headers, tablefmt="grid"))
        f.write("\n\nThese estimates are based on measurements with small candidate sets.\n")
        f.write("Actual performance may vary slightly depending on system load.\n")
    
    # Visualize the results
    plt.figure(figsize=(10, 6))
    plt.scatter(sizes, times, label='Measured', color='blue', s=50)
    
    # Plot the fitted curve
    x_smooth = np.linspace(0, max(table_sizes), 1000)
    y_smooth = estimate_time(x_smooth)
    plt.plot(x_smooth, y_smooth, 'r-', label='Quadratic fit')
    
    # Add points for the estimated larger sizes
    est_times = [estimate_time(s) for s in table_sizes]
    plt.scatter(table_sizes, est_times, color='green', label='Estimated', alpha=0.5, s=30)
    
    plt.xlabel('Number of candidates')
    plt.ylabel('Time (seconds)')
    plt.title('Runtime estimation for max_analysis_for_pattern')
    plt.legend()
    plt.grid(True)
    
    # Add the formula to the plot
    plt.text(0.5, 0.95, simplified_rule.replace("~=", "≈"), transform=plt.gca().transAxes, 
             horizontalalignment='center', bbox=dict(facecolor='white', alpha=0.8))
    
    # Save the plot
    plt.savefig('runtime_estimation.png')
    print("\nSaved estimation plot to 'runtime_estimation.png'")
    print("Saved estimation table to 'runtime_estimates.txt'")
    
    return {
        'coefficients': (a, b, c),
        'estimate_function': estimate_time,
        'rule': rule,
        'simplified_rule': simplified_rule,
        'sizes_tested': sizes,
        'times_measured': times,
        'table_data': table_data
    }

# Function to estimate runtime for all patterns
def estimate_pattern_distribution(pattern_counts, coef_a, coef_b, coef_c):
    """
    Estimate total runtime for a set of patterns with known candidate counts
    
    Args:
        pattern_counts: Dictionary mapping patterns to candidate counts
        coef_a, coef_b, coef_c: Coefficients from quadratic fit
    
    Returns:
        Estimated total runtime in hours and breakdown by pattern
    """
    def estimate_time(n):
        return coef_a * n**2 + coef_b * n + coef_c
    
    results = {}
    total_time = 0
    
    for pattern, count in pattern_counts.items():
        time_seconds = estimate_time(count)
        results[pattern] = {
            'candidates': count,
            'time_seconds': time_seconds,
            'time_readable': format_time(time_seconds)
        }
        total_time += time_seconds
    
    return {
        'total_seconds': total_time,
        'total_minutes': total_time / 60,
        'total_hours': total_time / 3600,
        'pattern_breakdown': results
    }

def format_time(seconds):
    """Format seconds into a human-readable string"""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.2f} minutes"
    else:
        return f"{seconds/3600:.2f} hours"

# Run this function directly to get time estimates:
if __name__ == "__main__":
    # You can adjust max_sample_size based on how much time you want to spend measuring
    results = estimate_runtime(max_sample_size=50, runs_per_size=3)
    
    print("\nTo use these coefficients in your code:")
    print(f"a, b, c = {results['coefficients'][0]:.8f}, {results['coefficients'][1]:.8f}, {results['coefficients'][2]:.8f}")
    print("time_seconds = a * (num_candidates)**2 + b * (num_candidates) + c")

# Function to estimate runtime for all patterns
def estimate_pattern_distribution(pattern_counts, coef_a, coef_b, coef_c):
    """
    Estimate total runtime for a set of patterns with known candidate counts
    
    Args:
        pattern_counts: Dictionary mapping patterns to candidate counts
        coef_a, coef_b, coef_c: Coefficients from quadratic fit
    
    Returns:
        Estimated total runtime in hours and breakdown by pattern
    """
    def estimate_time(n):
        return coef_a * n**2 + coef_b * n + coef_c
    
    results = {}
    total_time = 0
    
    for pattern, count in pattern_counts.items():
        time_seconds = estimate_time(count)
        results[pattern] = {
            'candidates': count,
            'time_seconds': time_seconds,
            'time_readable': format_time(time_seconds)
        }
        total_time += time_seconds
    
    return {
        'total_seconds': total_time,
        'total_minutes': total_time / 60,
        'total_hours': total_time / 3600,
        'pattern_breakdown': results
    }

def format_time(seconds):
    """Format seconds into a human-readable string"""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.2f} minutes"
    else:
        return f"{seconds/3600:.2f} hours"

# Run this function directly to get time estimates:
#if __name__ == "__main__":
    # You can adjust max_sample_size based on how much time you want to spend measuring
    # results = estimate_runtime(max_sample_size=40, runs_per_size=3)
    
    # print("\nTo use these coefficients in your code:")
    # print(f"a, b, c = {results['coefficients'][0]:.8f}, {results['coefficients'][1]:.8f}, {results['coefficients'][2]:.8f}")
    # print("time_seconds = a * (num_candidates)**2 + b * (num_candidates) + c")


# Use the coefficients from your runtime analysis
a, b, c = 0.00194527, 0.01506201, -0.02471843

# Analyze all patterns
results = analyze_pattern_distribution('aider_outcomes_with_candidates.json', a, b, c)

# Analyze excluding patterns with >200 candidates
results_filtered = analyze_pattern_distribution('aider_outcomes_with_candidates.json', a, b, c, max_candidates=200)