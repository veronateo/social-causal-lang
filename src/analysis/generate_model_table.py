import json
import os


def generate_table(results_path: str = 'outputs/model_results.json',
                   output_path: str = 'outputs/model_table.tex'):
    with open(results_path) as f:
        results = json.load(f)
    
    cv = results['cv_summary']
    
    # Model ordering and display names 
    models = [
        ('full',      'Full'),
        ('nocausal',  'No Causal Inference'),
        ('nopref',    'No Mental State Inference'),
        ('sem',       'No Pragmatics'),
    ]
    
    # Find which model is best for each metric (for bolding)
    best = {
        'nll':  min(models, key=lambda m: cv[m[0]]['nll']['mean'])[0],
        'rmse': min(models, key=lambda m: cv[m[0]]['rmse']['mean'])[0],
        'r':    max(models, key=lambda m: cv[m[0]]['r']['mean'])[0],
    }
    
    def fmt(key, metric, decimals=3):
        """Format a metric value with SE, bolding if best."""
        mean = cv[key][metric]['mean']
        se = cv[key][metric]['se']
        val = f'{mean:.{decimals}f} $\\pm$ {se:.{decimals}f}'
        if best[metric] == key:
            val = f'\\textbf{{{val}}}'
        return val
    
    # Build the table
    lines = []
    
    for key, name in models:
        nll_str  = fmt(key, 'nll')
        rmse_str = fmt(key, 'rmse')
        r_str    = fmt(key, 'r')
        lines.append(f'    {name:<30s} & {nll_str}   & {rmse_str}    & {r_str} \\\\')
    
    table_str = '\n'.join(lines)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(table_str)
        f.write('\n')
    
    print(table_str)
    print(f'\nSaved to {output_path}')


if __name__ == '__main__':
    generate_table()
