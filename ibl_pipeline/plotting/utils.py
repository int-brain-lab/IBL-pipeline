'''
general utility functions or classes for plotting
'''
import numpy as np


class RedBlueColorBar:
    '''
    Color scale blue - white - red, with white at 0 value.
    '''

    def __init__(self, max_val, min_val, ncolors=100):

        self.cmax = 255.
        self.cmin = 0.
        self.zrange = [[min_val, max_val]]
        color_values = np.linspace(self.cmin, self.cmax, ncolors)
        if max_val <= 0:
            self.colors = [[i, i, self.cmax] for i in color_values]
            self.mode = 'BlueWhite'
        elif min_val >= 0:
            self.colors = [[self.cmax, i, i] for i in color_values[::-1]]
            self.mode = 'WhiteRed'
        else:
            self.c0 = (-min_val)/(max_val - min_val)
            ncolors_pos = int(ncolors*(1 - self.c0))
            ncolors_neg = ncolors - ncolors_pos
            color_step = self.cmax/(ncolors_pos-1)
            colors_pos = [[self.cmax, i, i]
                          for i in np.linspace(self.cmin, self.cmax,
                                               ncolors_pos)]
            colors_neg = [[self.cmax - n*color_step,
                           self.cmax - n*color_step, self.cmax]
                          for n in np.arange(ncolors_neg)]
            self.colors = (colors_pos + colors_neg)[::-1]
            self.mode = 'BlueWhiteRed'

    def as_matplotlib(self):
        return (np.array(self.colors)/255).astype('float32').tolist()

    def as_plotly(self):
        if self.mode == 'BlueWhite':
            return [[0, 'blue'], [1, 'white']]
        elif self.mode == 'WhiteRed':
            return [[0, 'white'], [1, 'blue']]
        elif self.mode == 'BlueWhiteRed':
            return [[0, 'rgb({}, {}, {})'.format(*self.colors[0])],
                    [self.c0, 'white'],
                    [1, 'red']]
