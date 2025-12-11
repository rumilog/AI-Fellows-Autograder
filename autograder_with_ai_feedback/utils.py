import json
import os
import re
import yaml
import traceback
import torch
from ai_feedback import enhance_results_with_ai_feedback


def to_py(
        notebook_path,
        script_path,
        autograded_only=True,
        imports = ""
        ):
    """
    Convert a Jupyter notebook to a Python script.
    if autograded_only is True, only cells starting with '# AUTOGRADED' will be included in the script.
    Since the imports will be added to the script, the imports should be passed as a string.
    """
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    script_cells = []

    if autograded_only:
        script_cells += [imports]

    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            continue
        cell = cell['source']
        if len(cell) == 0:
            continue
        if autograded_only and not cell[0].startswith('# AUTOGRADED'):
            continue
        
        cell_source = ''.join(cell)
        
        # removing docstrings
        cell_source = re.sub(r'(\'\'\'.*?\'\'\')|(\"\"\".*?\"\"\")', '', cell_source, flags=re.DOTALL)
        # remove all comments
        cell_source = re.sub(r'#.*', '', cell_source)

        # checking if there is any import statement in the cell if autograded_only is True
        # anything like import x or from this import that. use re to match import with surrounding spaces
        if autograded_only:
            assert not re.search(r'(?<!\w)import(?!\w)', cell_source), \
                f'Found import statement in your code. Please remove it!'

        script_cells.append(cell_source)

    script_source = ('\n\n'+100*'#'+'\n\n').join(script_cells)
    script_source = re.sub(r'\n\s*\n', '\n\n', script_source)
    # Replace print statements with pass at the same indentation level
    script_source = re.sub(r'^(\s*)print\s*\((.*)\)\s*$', r'\1pass', script_source, flags=re.MULTILINE)

    with open(script_path, 'w', encoding='utf-8') as f:
        # using regex to remove docstrings:
        f.write(script_source)
    return script_source


def make_py(autograder_dir: str, imports: str, solution=True):
    notebooks = [f for f in os.listdir(f'{autograder_dir}/submission') if f.endswith('.ipynb')]
    assert len(notebooks) == 1, f'Expected 1 notebook in submission, found {len(notebooks)}'
    if solution:
        to_py(f'{autograder_dir}/source/solution.ipynb', f'{autograder_dir}/source/solution.py', autograded_only=False)
    return to_py(f'{autograder_dir}/submission/{notebooks[0]}', f'{autograder_dir}/source/submission.py', imports=imports)


def load_yaml(yaml_path):
    with open(yaml_path, 'r') as f:
        return yaml.load(f, Loader=yaml.FullLoader)
    

def load_model(model_class, config_path, state_dict_path):
    model_config = load_yaml(config_path)
    model: torch.nn.Module = model_class(**model_config)
    model.load_state_dict(torch.load(state_dict_path))
    return model


def save_results(results: dict, autograder_dir: str):
    
    results = enhance_results_with_ai_feedback(results, autograder_dir)
with open(f'{autograder_dir}/results/results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)


# Decorator to catch errors of a grader function
def grader(action, name=None, max_score=None):

    def decorator(test_func):

        def wrapper(*args, **kwargs):
            
            try:
                result = test_func(*args, **kwargs) # {'score': score, 'output': output}

            except Exception as e:

                tb = traceback.format_exc()
                tb_lines = tb.splitlines()
                filtered_tb_lines = []
                include_next_line = False
                for line in tb_lines:
                    # If the error is in student submission:
                    if "/autograder/source/submission.py" in line:
                        include_next_line = True
                        error_location = line.split(',')[-1].strip() + ':'
                        # Get line number of the code from this line
                    elif include_next_line:
                        # Include the code line following the module path
                        filtered_tb_lines.append(error_location+'\n'+line)
                        include_next_line = False
                
                # Always include the last line (the exception type and message)
                filtered_tb_lines.append(tb_lines[-1])

                # concatenate the lines
                output = ('\n'+50*'-'+'\n').join(filtered_tb_lines)

                result = {
                    'score': 0.0,
                    'output': output,
                }

            if name is not None:
                result['name'] = name
            if max_score is not None:
                result['max_score'] = max_score
                
            return result
        
        return wrapper
    
    return decorator