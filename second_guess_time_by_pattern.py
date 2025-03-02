import json
import pandas as pd

def create_pattern_runtime_df(json_file, a, b, c):
    """
    Create DataFrame with patterns, candidate counts, and estimated runtimes
    
    Args:
        json_file: Path to JSON file with pattern data
        a, b, c: Coefficients for runtime estimation formula
        
    Returns:
        DataFrame with pattern info and runtime estimates
    """
    # Load the JSON data
    with open(json_file, 'r') as f:
        patterns_data = json.load(f)
    
    # Extract data for each pattern
    data = []
    for pattern, info in patterns_data.items():
        if "remaining_candidates" in info:
            count = info["remaining_candidates"]["count"]
            # Calculate estimated runtime using the formula
            est_time = a * (count**2) + b * count + c
            
            # Create readable time string
            if est_time < 60:
                time_str = f"{est_time:.2f} seconds"
            elif est_time < 3600:
                time_str = f"{est_time/60:.2f} minutes"
            else:
                time_str = f"{est_time/3600:.2f} hours"
            
            data.append({
                'Pattern': pattern,
                'Candidate_Count': count,
                'Runtime_Seconds': est_time,
                'Runtime_Readable': time_str
            })
    
    # Create DataFrame and sort by estimated runtime
    df = pd.DataFrame(data)
    df = df.sort_values('Runtime_Seconds', ascending=False)
    
    print(f"Created DataFrame with {len(df)} patterns")
    print(f"Total estimated runtime: {df['Runtime_Seconds'].sum()/3600:.2f} hours")
    
    return df


import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def plot_runtime_vs_count(df, a, b, c, save_path='runtime_scatter.png'):
    """
    Create a scatter plot of candidate count vs runtime with the fitted curve
    
    Args:
        df: DataFrame with Candidate_Count and Runtime_Seconds columns
        a, b, c: Coefficients for the quadratic formula
        save_path: Path to save the plot
    """
    # Create plot
    plt.figure(figsize=(12, 8))
    
    # Scatter plot of actual data points
    plt.scatter(df['Candidate_Count'], df['Runtime_Seconds'], 
                alpha=0.7, color='blue', label='Patterns')
    
    # Add quadratic curve
    x_range = np.linspace(0, df['Candidate_Count'].max() * 1.05, 1000)
    y_pred = a * x_range**2 + b * x_range + c
    plt.plot(x_range, y_pred, 'r-', linewidth=2, 
             label=f'Quadratic model: {a:.6f}x² + {b:.6f}x + {c:.6f}')
    
    # Add labels and title
    plt.xlabel('Candidate Count', fontsize=14)
    plt.ylabel('Runtime (seconds)', fontsize=14)
    plt.title('Candidate Count vs Estimated Runtime', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Add annotations for some points
    top_points = df.nlargest(5, 'Candidate_Count')
    for _, row in top_points.iterrows():
        plt.annotate(f"{row['Pattern']} ({row['Candidate_Count']})",
                    (row['Candidate_Count'], row['Runtime_Seconds']),
                    xytext=(10, 5), textcoords='offset points',
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))
    
    # Save and show
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.show()
    print(f"Plot saved to {save_path}")
    
    # Create a second plot with log scale for better visibility
    plt.figure(figsize=(12, 8))
    plt.scatter(df['Candidate_Count'], df['Runtime_Seconds'], 
                alpha=0.7, color='blue', label='Patterns')
    plt.plot(x_range, y_pred, 'r-', linewidth=2, 
             label=f'Quadratic model')
    
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Candidate Count (log scale)', fontsize=14)
    plt.ylabel('Runtime (seconds, log scale)', fontsize=14)
    plt.title('Candidate Count vs Runtime (Log Scale)', fontsize=16)
    plt.grid(True, alpha=0.3, which='both')
    plt.legend(fontsize=12)
    
    # Save and show log plot
    plt.tight_layout()
    plt.savefig('runtime_scatter_log.png', dpi=300)
    print(f"Log scale plot saved to runtime_scatter_log.png")



# if __name__ == "__main__":
#     # Runtime estimation coefficients
#     a, b, c = 0.00454187, -0.04628192, 0.20732144
    
#     # Create and display the DataFrame
#     df = create_pattern_runtime_df('aider_outcomes_with_candidates.json', a, b, c)
    
#     # Show the top patterns by runtime
#     print("\nTop 10 patterns by runtime:")
#     print(df.head(10)[['Pattern', 'Candidate_Count', 'Runtime_Seconds', 'Runtime_Readable']])
    
#     # Save to CSV
#     df.to_csv('pattern_runtimes.csv', index=False)
#     print("\nSaved DataFrame to pattern_runtimes.csv")


# Example usage:
# if __name__ == "__main__":
#     # Load DataFrame (either from CSV or from the previous function)
#     try:
#         df = pd.read_csv('pattern_runtimes.csv')
#     except FileNotFoundError:
#         print("pattern_runtimes.csv not found, please run the previous script first")
#         exit()
    
#     # Runtime estimation coefficients
#     a, b, c = 0.00454187, -0.04628192, 0.20732144
    
#     # Create the plot
#     plot_runtime_vs_count(df, a, b, c)

if __name__ == "__main__":
    a,b,c = 0.00454187, -0.04628192, 0.20732144
    df = create_pattern_runtime_df('aider_outcomes_with_candidates.json', a, b, c)
    num_seconds = df["Runtime_Seconds"].sum()
    print(f"Total estimated runtime: {num_seconds/3600:.2f} hours")