from matplotlib import rcParams


COLORS = {
    'caused': '#e74c3c',
    'enabled': '#f39c12',
    'allowed': '#3498db',
    'made_no_difference': '#95a5a6'
}

rcParams.update({
    # Font
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica'],
    'font.size': 10,
    'font.weight': 'normal',

    # Figure
    'figure.dpi': 600,
    'figure.facecolor': 'white',
    'figure.constrained_layout.use': True,

    # Axes
    'axes.titlesize': 12,
    'axes.titleweight': 'normal',
    'axes.labelsize': 10,
    'axes.labelweight': 'normal',
    'axes.edgecolor': '#808080',
    'axes.linewidth': 0.8,
    'axes.spines.left': True,
    'axes.spines.bottom': True,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.axisbelow': True,

    # Ticks
    'xtick.labelsize': 9,
    'xtick.color': '#808080',
    'xtick.labelcolor': '#666666',
    'ytick.labelsize': 9,
    'ytick.color': '#808080',
    'ytick.labelcolor': '#666666',

    # Legend
    'legend.fontsize': 9,
    'legend.frameon': True,
    'legend.fancybox': True,
    'legend.framealpha': 1.0,
    'legend.handlelength': 1.2,
    'legend.handleheight': 1.2,

    # Lines
    'lines.linewidth': 1.5,

    # Grid
    'grid.color': '#B0B0B0',
    'grid.linestyle': '-',
    'grid.linewidth': 0.5,
    'grid.alpha': 0.3,

    # Saving
    'savefig.dpi': 600,
    'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
})
