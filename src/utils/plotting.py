from matplotlib import rcParams


class Colors:
    OKABE_ITO = {
        'light_blue': '#56B4E9',
        'orange': '#E69F00',
        'green': '#009E73',
        'yellow': '#F0E442',
        'blue': '#0072B2',
        'amber': '#D55E00',
        'pink': '#CC79A7',
        'black': '#000000'
    }

    # Semantic aliases
    SKY_BLUE = OKABE_ITO['light_blue']
    BLUE = OKABE_ITO['blue']
    ORANGE = OKABE_ITO['orange']
    TEAL_GREEN = OKABE_ITO['green']
    PINK = OKABE_ITO['pink']
    AMBER = OKABE_ITO['amber']
    YELLOW = OKABE_ITO['yellow']
    BLACK = OKABE_ITO['black']
    LIGHT_GRAY = '#D5D5D5'
    GREEN = '#58C24F'
    RED = '#FA5A4D'
    LIGHT_RED = '#F7A5A1'
    LIGHT_GREEN = '#AFE29F'


colors = Colors()


rcParams.update({
    # Font
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica', 'DejaVu Sans', 'Arial', 'sans-serif'],
    'font.size': 10,
    'font.weight': 'normal',

    # Figure
    'figure.dpi': 300,
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
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
})
