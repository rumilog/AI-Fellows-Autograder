"""
Test script to demonstrate the AI feedback functionality
"""

import json
from ai_feedback import enhance_results_with_ai_feedback
import tempfile
import os

# Create a mock autograder directory structure
def setup_test_environment():
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    # Create submission directory
    submission_dir = os.path.join(temp_dir, 'submission')
    os.makedirs(submission_dir)
    
    # Create source directory  
    source_dir = os.path.join(temp_dir, 'source')
    os.makedirs(source_dir)
    
    # Create a sample student submission (Python file)
    submission_py = os.path.join(source_dir, 'submission.py')
    with open(submission_py, 'w') as f:
        f.write("""
# AUTOGRADED
def conv2d(Input, Kernel, Bias, stride, padding, dilation, groups):
    # Student implementation of convolution
    # This is a simplified version with issues
    output = Input @ Kernel  # Wrong operation
    return output + Bias

# AUTOGRADED  
def avg_pool2d(Input, kernel_size, stride, padding):
    # Incorrect pooling implementation
    return Input[:kernel_size[0], :kernel_size[1]]  # Just slicing, not pooling
""")
    
    return temp_dir


def main():
    print("Testing AI Feedback Generator")
    print("=" * 50)
    
    # Sample autograder results
    sample_results = {
        "tests": [
            {
                "name": "simple convolution",
                "score": 0,
                "max_score": 10,
                "output": "AssertionError: Tensor shapes do not match. Expected (5, 5, 6) but got (3, 5)"
            },
            {
                "name": "padding, stride",
                "score": 0,
                "max_score": 20,
                "output": "TypeError: unsupported operand type(s) for @: 'numpy.ndarray' and 'numpy.ndarray'"
            },
            {
                "name": "average pooling",
                "score": 0,
                "max_score": 10,
                "output": "AssertionError: Output shape mismatch. Your function returns wrong dimensions."
            },
            {
                "name": "for loops",
                "score": -10,
                "max_score": 0,
                "output": "Number of additional for loops: 2"
            }
        ],
        "output": "autograder runtime: 2.34 seconds",
        "execution_time": 2
    }
    
    # Setup test environment
    test_dir = setup_test_environment()
    
    print(f"Created test environment at: {test_dir}")
    print("\nOriginal Results:")
    print(json.dumps(sample_results, indent=2))
    
    # Test the enhancement
    print("\n" + "=" * 50)
    print("Enhancing with AI Feedback...")
    print("=" * 50 + "\n")
    
    try:
        enhanced_results = enhance_results_with_ai_feedback(sample_results, test_dir)
        
        print("Enhanced Results with AI Feedback:")
        print(json.dumps(enhanced_results, indent=2))
        
        # Check if feedback was added
        if 'ai_feedback' in enhanced_results:
            print("\n✓ Overall AI feedback added successfully!")
        
        feedback_count = sum(1 for test in enhanced_results.get('tests', []) if 'ai_feedback' in test)
        print(f"✓ AI feedback added to {feedback_count}/{len(enhanced_results.get('tests', []))} tests")
        
    except Exception as e:
        print(f"Error during enhancement: {e}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print("\n✓ Test environment cleaned up")


if __name__ == "__main__":
    main()
