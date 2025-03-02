import json
import pandas as pd
import os
import time
import argparse
from datetime import datetime
from expected_value import perform_full_analysis

def run_analysis_on_filtered_patterns(json_file, output_file, max_candidates=200, test_mode=False):
    """
    Load patterns from JSON, filter by candidate count, run analysis on each,
    and save results incrementally.
    
    Args:
        json_file: Path to JSON file containing pattern data
        output_file: Path to save results to
        max_candidates: Maximum number of candidates to process a pattern
        test_mode: If True, only process a few patterns with low candidate counts
    
    Returns:
        Dictionary of analysis results
    """
    # Modify output filename if in test mode
    if test_mode:
        base_name, ext = os.path.splitext(output_file)
        output_file = f"{base_name}_TESTING{ext}"
    
    # Load the pattern data
    print(f"\n=== Pattern Analysis ===")
    print(f"Input: {json_file}")
    print(f"Output: {output_file}")
    print(f"Max candidates: {max_candidates}")
    print(f"Test mode: {test_mode}")
    
    try:
        with open(json_file, 'r') as f:
            filtered_data = json.load(f)
        print(f"Successfully loaded {len(filtered_data)} patterns from {json_file}")
    except Exception as e:
        print(f"Error loading {json_file}: {str(e)}")
        return {}
    
    # Filter patterns by candidate count
    patterns_to_process = {}
    candidate_counts = []
    
    for pattern, data in filtered_data.items():
        candidate_count = data["remaining_candidates"]["count"]
        candidate_counts.append((pattern, candidate_count))
        
        if candidate_count <= max_candidates:
            patterns_to_process[pattern] = data
    
    # Sort by candidate count for more efficient processing (start with smaller ones)
    candidate_counts.sort(key=lambda x: x[1])
    
    total_patterns = len(filtered_data)
    filtered_patterns = len(patterns_to_process)
    skipped_patterns = total_patterns - filtered_patterns
    
    print(f"\nPattern statistics:")
    print(f"- Total patterns: {total_patterns}")
    print(f"- Patterns with ≤ {max_candidates} candidates: {filtered_patterns}")
    print(f"- Patterns with > {max_candidates} candidates (skipped): {skipped_patterns}")
    
    # In test mode, select just a few patterns with low counts
    if test_mode:
        # Get up to 3 patterns with the lowest counts
        test_patterns = {pattern: filtered_data[pattern] for pattern, count in candidate_counts[:3] if count <= 10}
        
        if not test_patterns:
            # If no patterns have <10 candidates, take the smallest ones available up to 3
            test_patterns = {pattern: filtered_data[pattern] for pattern, count in candidate_counts[:3] if count <= max_candidates}
        
        patterns_to_process = test_patterns
        print(f"\nTEST MODE: Processing only {len(test_patterns)} patterns:")
        for pattern, data in test_patterns.items():
            print(f"- {pattern}: {data['remaining_candidates']['count']} candidates")
    
    # Check if output file exists and load existing results
    results = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                results = json.load(f)
            print(f"\nFound existing results file with {len(results)} patterns")
        except json.JSONDecodeError:
            print(f"\nCould not decode existing file {output_file}, starting fresh")
    
    # Determine which patterns still need processing
    patterns_remaining = {
        pattern: filtered_data[pattern] 
        for pattern in patterns_to_process 
        if pattern not in results
    }
    
    if not patterns_remaining:
        print("\nAll patterns have already been processed!")
        return results
    
    print(f"\nPatterns to process: {len(patterns_remaining)}")
    
    # Process each pattern and save results incrementally
    total_start_time = time.time()
    processed_count = 0
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\nStarting analysis at {start_time}")
    print("-" * 60)
    
    # Sort patterns by candidate count in ascending order
    patterns_to_process_sorted = sorted(
        patterns_remaining.items(),
        key=lambda x: x[1]["remaining_candidates"]["count"]
    )
    
    # Time estimation constants
    a, b, c = 0.00454187, -0.04628192, 0.20732144
    
    # Calculate total estimated time for all remaining patterns
    total_estimated_time = 0
    for pattern, data in patterns_to_process_sorted:
        candidate_count = data["remaining_candidates"]["count"]
        pattern_time = a * (candidate_count)**2 + b * (candidate_count) + c
        total_estimated_time += pattern_time
    
    print(f"Estimated total time for all patterns: {format_time(total_estimated_time)}")
    print("-" * 60)
    
    for i, (pattern, data) in enumerate(patterns_to_process_sorted, 1):
        candidate_count = data["remaining_candidates"]["count"]
        
        # Estimate time for this pattern
        estimated_time = a * (candidate_count)**2 + b * (candidate_count) + c
        
        # Calculate remaining time for patterns after this one
        remaining_time = 0
        if i < len(patterns_to_process_sorted):
            for j in range(i, len(patterns_to_process_sorted)):
                next_pattern, next_data = patterns_to_process_sorted[j]
                next_count = next_data["remaining_candidates"]["count"]
                next_time = a * (next_count)**2 + b * (next_count) + c
                remaining_time += next_time
        
        print(f"Pattern {i}/{len(patterns_remaining)}: {pattern} ({candidate_count} candidates)")
        print(f"  Estimated time for this pattern: {format_time(estimated_time)}")
        print(f"  Estimated time for all remaining patterns: {format_time(remaining_time)}")
        
        # Process timing
        pattern_start_time = time.time()
        
        # Run the analysis
        try:
            analysis_result = max_analysis_for_pattern(pattern, filtered_data)
            results[pattern] = analysis_result
            processed_count += 1
            
            # Save the updated results after each pattern
            try:
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                save_status = "Success"
            except Exception as e:
                save_status = f"Error: {str(e)}"
            
            # Log completion
            elapsed = time.time() - pattern_start_time
            per_candidate = elapsed / candidate_count if candidate_count > 0 else 0
            
            print(f"  Completed in {format_time(elapsed)} ({format_time(per_candidate)} per candidate)")
            print(f"  Save: {save_status}")
            
            # Estimate remaining time
            if i < len(patterns_to_process_sorted):
                # Calculate remaining time based on our time function
                remaining_time = 0
                for j in range(i, len(patterns_to_process_sorted)):
                    next_pattern, next_data = patterns_to_process_sorted[j]
                    next_count = next_data["remaining_candidates"]["count"]
                    next_time = a * (next_count)**2 + b * (next_count) + c
                    remaining_time += next_time
                
                print(f"  Updated estimated remaining time: {format_time(remaining_time)}")
                
                # Also show the traditional estimate based on average processing time
                if processed_count > 0:
                    remaining_patterns = len(patterns_remaining) - i
                    avg_time_per_pattern = (time.time() - total_start_time) / processed_count
                    est_remaining = avg_time_per_pattern * remaining_patterns
                    print(f"  Average-based remaining time: {format_time(est_remaining)}")
            
            print("-" * 60)
            
        except Exception as e:
            print(f"  Error processing pattern {pattern}: {str(e)}")
            print("-" * 60)
    
    # Final stats
    total_elapsed = time.time() - total_start_time
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\nAnalysis complete at {end_time}!")
    print(f"Started: {start_time}")
    print(f"Total processing time: {format_time(total_elapsed)}")
    print(f"Successfully processed: {processed_count}/{len(patterns_remaining)} patterns")
    print(f"Results saved to: {output_file}")
    
    if test_mode:
        print("\nTEST MODE NOTE: This was a test run with limited patterns.")
        print("Run without test_mode=True for full processing.")
    
    return results

def max_analysis_for_pattern(pattern, filtered_data):
    """
    Run analysis for a given pattern.
    
    Args:
        pattern: The pattern to analyze
        filtered_data: Dictionary containing pattern data
    
    Returns:
        Analysis results
    """
    # Get candidates for the pattern
    candidates = filtered_data[pattern]["remaining_candidates"]["words"]
    candidates_df = pd.DataFrame({"WORD": candidates})
    
    # Run the analysis
    result = perform_full_analysis(candidates, candidates_df)
    
    # Convert DataFrame to serializable format
    if isinstance(result, pd.DataFrame):
        return result.to_dict('records')
    elif isinstance(result, tuple) and any(isinstance(item, pd.DataFrame) for item in result):
        # If the result is a tuple with DataFrames inside
        serialized_result = []
        for item in result:
            if isinstance(item, pd.DataFrame):
                serialized_result.append(item.to_dict('records'))
            else:
                serialized_result.append(item)
        return serialized_result
    
    return result

def format_time(seconds):
    """Convert seconds to a human-readable format."""
    if seconds < 0.1:
        return f"{seconds*1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f} minutes"
    else:
        hours = seconds / 3600
        days = hours / 24
        if days >= 1:
            return f"{days:.2f} days"
        return f"{hours:.2f} hours"

if __name__ == "__main__":
    # Configuration variables
    input_file = "aider_outcomes_filtered.json"
    output_file = "pattern_analysis_results.json"
    max_candidate_count = 500
    test_mode = False  # Set to True to run a test on just a few patterns
    
    # Run the analysis
    results = run_analysis_on_filtered_patterns(
        input_file, 
        output_file, 
        max_candidate_count, 
        test_mode
    )