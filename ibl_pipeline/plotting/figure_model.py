import base64
import gc
import io

import imageio
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.figure import Figure


class PngFigure(Figure):
    def __init__(
        self,
        draw,
        data,
        ax_kwargs={},
        dpi=50,
        frameon=False,
        figsize=[8, 6],
        transparent=False,
        axes_off=True,
    ):

        super().__init__(dpi=dpi, frameon=frameon, figsize=figsize)
        ax = Axes(self, [0.0, 0.0, 1.0, 1.0])
        if axes_off:
            ax.set_axis_off()

        result = draw(**data, **ax_kwargs, ax=ax)

        # if draw function only returns the axes
        if isinstance(result, Axes):
            ax = result
        else:
            (ax, self.x_lim, self.y_lim) = result[0:3]
            if len(result) > 3:
                self.other_returns = result[3:]

        self.add_axes(ax)

        self.buffer = io.BytesIO()
        self.savefig(
            self.buffer, transparent=transparent, dpi=dpi, pad_inches=0, format="png"
        )

    def upload_to_s3(self, bucket, fig_link):
        self.buffer.seek(0)
        bucket.put_object(Body=self.buffer, ContentType="image/png", Key=fig_link)

    @property
    def encoded_string(self):
        self.buffer.seek(0)
        return base64.b64encode(self.buffer.read())

    def create_layout_template(
        self, with_encoded_string=True, x_title=None, y_title=None
    ):

        if with_encoded_string:
            source = "data:image/png;base64, " + self.encoded_string.decode()
        else:
            source = "data:image/png;base64, "

        if not (hasattr(self, "x_lim") and hasattr(self, "y_lim")):
            raise AttributeError("Attributes x_lim or y_lim are not defined.")

        return dict(
            images=[
                dict(
                    source=source,
                    sizex=self.x_lim[1] - self.x_lim[0],
                    sizey=self.y_lim[1] - self.y_lim[0],
                    x=self.x_lim[0],
                    y=self.y_lim[1],
                    xref="x",
                    yref="y",
                    sizing="stretch",
                    layer="below",
                )
            ],
            xaxis=dict(
                title=x_title, showgrid=False, range=self.x_lim, ticks="outside"
            ),
            yaxis=dict(
                title=dict(text=y_title, standoff=10),
                showgrid=False,
                range=self.y_lim,
                ticks="outside",
            ),
        )

    def cleanup(self):
        # clean up figure and memory
        self.clear()
        plt.close(self)
        gc.collect()


class GifFigure:
    def __init__(
        self,
        draw,
        trajectories,
        duration_per_cycle=5,
        nframes_per_cycle=30,
        figsize=[800, 700],
    ):

        frames = draw(
            trajectories, nframes_per_cycle=nframes_per_cycle, figsize=figsize
        )

        self.buffer = io.BytesIO()
        imageio.mimwrite(
            self.buffer, frames, "gif", duration=duration_per_cycle / nframes_per_cycle
        )

    def upload_to_s3(self, bucket, fig_link):
        self.buffer.seek(0)
        bucket.put_object(Body=self.buffer, Key=fig_link)
