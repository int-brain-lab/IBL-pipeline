import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import seaborn as sns
import io
import base64
import gc


class PngFigure(Figure):

    def __init__(self, draw, data, ax_kwargs,
                 dpi=50, frameon=False, figsize=[8, 6]):

        super().__init__(dpi=dpi, frameon=frameon, figsize=figsize)
        ax = Axes(self, [0., 0., 1., 1.])
        ax, self.x_lim, self.y_lim = draw(**data, **ax_kwargs, ax=ax)
        self.add_axes(ax)

        self.buffer = io.BytesIO()
        self.savefig(self.buffer, pad_inches=0, format='png')

    def upload_to_s3(self, bucket, fig_link):
        self.buffer.seek(0)
        bucket.put_object(Body=self.buffer,
                          ContentType='image/png',
                          Key=fig_link)

    @property
    def encoded_string(self):
        self.buffer.seek(0)
        return base64.b64encode(self.buffer.read())

    def create_layout_template(self, with_encoded_string=True,
                               x_title=None, y_title=None):

        if with_encoded_string:
            source = 'data:image/png;base64, ' + self.encoded_string.decode()
        else:
            source = 'data:image/png;base64, '

        return dict(
            images=[dict(source=source,
                         sizex=self.x_lim[1] - self.x_lim[0],
                         sizey=self.y_lim[1] - self.y_lim[0],
                         x=self.x_lim[0],
                         y=self.y_lim[1],
                         xref='x',
                         yref='y',
                         sizing='stretch',
                         layer='below')],
            xaxis=dict(
                title=x_title,
                showgrid=False,
                range=self.x_lim),
            yaxis=dict(
                title=y_title,
                showgrid=False,
                range=self.y_lim)
        )

    def cleanup(self):
        # clean up figure and memory
        self.clear()
        plt.close(self)
        gc.collect()
