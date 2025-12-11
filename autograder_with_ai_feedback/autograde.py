import os
import argparse
from utils import make_py, save_results, grader
import torch
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Union
import re
import time

IMPORTS = """
import numpy as np
from typing import Tuple, Union

def to_tuple(
        x: Union[int, Tuple[int, int]]
        ) -> Tuple[int, int]:
    
    if isinstance(x, tuple):
        return x
    return (x, x)
"""

def to_tuple(
        x: Union[int, Tuple[int, int]]
        ) -> Tuple[int, int]:
    
    if isinstance(x, tuple):
        return x
    return (x, x)


def test(conv2d, config):

    c_in = config['c_in']
    c_out = config['c_out']
    X_in = config['X_in']
    Y_in = config['Y_in']
    X_k = config['X_k']
    Y_k = config['Y_k']
    stride = config['stride']
    padding = config['padding']
    dilation = config['dilation']
    groups = config['groups']

    # Test the function with 5 random inputs
    for i in range(3):

        np.random.seed(i)
        # Random input, kernel and bias
        Input = np.random.randn(c_in, X_in, Y_in).astype(np.float32)
        Kernel = np.random.randn(c_out, c_in//groups, X_k, Y_k).astype(np.float32)
        Bias = np.random.randn(c_out).astype(np.float32)

        # Calculate the output using your function
        your_output = conv2d(Input, Kernel, Bias, stride, padding, dilation, groups).astype(np.float32)

        # Calculate the output using PyTorch
        Input_torch = torch.tensor(Input[None, ...]) # A dummy dimension as the batch dimension
        Kernel_torch = torch.tensor(Kernel)
        Bias_torch = torch.tensor(Bias)
        torcX_output = F.conv2d(Input_torch, Kernel_torch, Bias_torch, stride=stride, padding=padding, dilation=dilation, groups=groups)[0]

        # Calculate the relative L2 norm error
        # If your output is of the wrong shape, this will raise an error
        torch.testing.assert_close(torch.as_tensor(your_output), torcX_output, atol=1e-3, rtol=1e-3)


def test_pool(avg_pool2d, config):

    c = config['c']
    X_in = config['X_in']
    Y_in = config['Y_in']
    X_k = config['X_k']
    Y_k = config['Y_k']
    stride = config['stride']
    padding = config['padding']

    # Test the function with 5 random inputs
    for i in range(3):

        np.random.seed(i)

        # Random input and kernel
        Input = np.random.randn(c, X_in, Y_in).astype(np.float32)

        # Calculate the output using your function
        your_output = avg_pool2d(Input, (X_k, Y_k), stride, padding).astype(np.float32)

        # Calculate the output using PyTorch
        Input_torch = torch.tensor(Input[None, ...]) # A dummy dimension as the batch dimension
        torch_output = F.avg_pool2d(Input_torch, (X_k, Y_k), stride=stride, padding=padding)[0]

        # Calculate the relative L2 norm error
        # If your output is of the wrong shape, this will raise an error
        torch.testing.assert_close(torch.as_tensor(your_output), torch_output, atol=1e-3, rtol=1e-3)


####################################################################################################


@grader('testing simple convolution', name='simple convolution', max_score=10)
def test_simple_convolution(submission):
    config = {
        'c_in': 3,
        'c_out': 5,
        'X_in': 7,
        'Y_in': 8,
        'X_k': 3,
        'Y_k': 4,
        'stride': 1,
        'padding': 0,
        'dilation': 1,
        'groups': 1,
    }
    test(submission.conv2d, config)
    config.update({'X_k': 4, 'Y_k': 3})
    test(submission.conv2d, config)
    return {'score': 10}


@grader('testing with padding', name='padding', max_score=20)
def test_padded_convolution(submission):
    config = {
        'c_in': 3,
        'c_out': 5,
        'X_in': 7,
        'Y_in': 8,
        'X_k': 3,
        'Y_k': 4,
        'stride': 1,
        'padding': (1, 2),
        'dilation': 1,
        'groups': 1,
    }
    test(submission.conv2d, config)
    config['padding'] = (2, 3)
    test(submission.conv2d, config)
    return {'score': 20}


@grader('testing with padding & stride', name='padding, stride', max_score=20)
def test_strided_convolution(submission):
    config = {
        'c_in': 3,
        'c_out': 5,
        'X_in': 11,
        'Y_in': 13,
        'X_k': 3,
        'Y_k': 4,
        'stride': (2, 3),
        'padding': (1, 2),
        'dilation': 1,
        'groups': 1,
    }
    test(submission.conv2d, config)
    config['stride'] = (3, 2)
    test(submission.conv2d, config)
    return {'score': 20}


@grader('testing with padding, stride, dilation', name='padding, stride, dilation', max_score=20)
def test_dilated_convolution(submission):
    config = {
        'c_in': 3,
        'c_out': 5,
        'X_in': 23,
        'Y_in': 29,
        'X_k': 3,
        'Y_k': 4,
        'stride': (2, 3),
        'padding': (3, 2),
        'dilation': (2, 1),
        'groups': 1,
    }
    test(submission.conv2d, config)
    config['dilation'] = (1, 2)
    test(submission.conv2d, config)
    return {'score': 20}


@grader('testing with padding, stride, dilation, groups', name='padding, stride, dilation, groups', max_score=20)
def test_grouped_convolution(submission):
    config = {
        'c_in': 8,
        'c_out': 12,
        'X_in': 17,
        'Y_in': 19,
        'X_k': 3,
        'Y_k': 4,
        'stride': (2, 3),
        'padding': (1, 2),
        'dilation': (2, 1),
        'groups': 4,
    }
    test(submission.conv2d, config)
    return {'score': 20}


@grader('testing average pooling', name='average pooling', max_score=10)
def test_avg_pool2d(submission):
    config = {
        'c': 3,
        'X_in': 17,
        'Y_in': 19,
        'X_k': 3,
        'Y_k': 4,
        'stride': (2, 3),
        'padding': (1, 0),
    }
    test_pool(submission.avg_pool2d, config)
    config.update({'X_k': 4, 'Y_k': 3})
    test_pool(submission.avg_pool2d, config)
    return {'score': 10}

####################################################################################################

@grader('Autograding')
def Grade(autograder_dir):
    start_time = time.time()
    source_script = make_py(autograder_dir, IMPORTS, solution=False)
    submission = __import__('submission')
    
    # use regex to count the number of for loops in the source_sript
    # the pattern is for something in something

    # count the number of for loops in the source_script
    num_for_loops = len(re.findall(r"\s*for\s+\w+\s+in\s+", source_script))
    for_penalty = (num_for_loops-2)*5

    results = {}
    results['tests']= [
        test_simple_convolution(submission),
        test_padded_convolution(submission),
        test_strided_convolution(submission),
        test_dilated_convolution(submission),
        test_grouped_convolution(submission),
        test_avg_pool2d(submission),
        {
            'name': 'for loops',
            'score': -for_penalty,
            'max_score': 0,
            'output': f'Number of additional for loops: {num_for_loops-2}',
        }
    ]
    end_time = time.time()
    results['output'] = f'autograder runtime: {end_time - start_time:.2f} seconds'
    results['execution_time'] = round(end_time - start_time)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('autograder_dir', type=str)
    args = parser.parse_args()
    os.makedirs(args.autograder_dir+'/results', exist_ok=True)
    results = Grade(args.autograder_dir)
    save_results(results, args.autograder_dir)
