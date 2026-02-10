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
    lines.append(r'\begin{table}[b]')
    lines.append(r'    \caption{Model performance comparison on $5$-fold cross validation. '
                 r'We randomly split the $38$ trials into 5 folds, fitting parameters on '
                 r'training folds and evaluating on the held-out test fold. Values represent '
                 r'means $\pm$ standard error for each metric are averaged on the test trials. '
                 r'$\downarrow$ means lower values are better. ')
    lines.append(r'    % \textit{Note}: ')
    lines.append(r'    NLL $=$ negative log-likelihood, RMSE $=$ root mean squared error, '
                 r'r $=$ Pearson correlation.}')
    lines.append(r'    \label{tab:model_comparison}')
    lines.append(r'    \centering')
    lines.append(r'    \resizebox{\columnwidth}{!}{')
    lines.append(r'    \begin{tabular}{lcccc}')
    lines.append(r'    \toprule')
    lines.append(r'    Model & $\downarrow$ NLL & $\downarrow$ RMSE & $\uparrow$ $r$\\')
    lines.append(r'    \midrule')
    
    for key, name in models:
        nll_str  = fmt(key, 'nll')
        rmse_str = fmt(key, 'rmse')
        r_str    = fmt(key, 'r')
        lines.append(f'    {name:<30s} & {nll_str}   & {rmse_str}    & {r_str} \\\\')
    
    lines.append(r'    \bottomrule')
    lines.append(r'    \end{tabular}')
    lines.append(r'    }')
    lines.append(r'\end{table}')
    
    table_str = '\n'.join(lines)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(table_str)
        f.write('\n')
    
    print(table_str)
    print(f'\nSaved to {output_path}')


if __name__ == '__main__':
    generate_table()
