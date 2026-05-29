import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Rectangle


PITCH_LENGTH = 120
PITCH_WIDTH = 80


def draw_pitch(ax=None):
    """Draw a simple StatsBomb-coordinate football pitch."""
    if ax is None:
        _, ax = plt.subplots(figsize=(12, 8))

    pitch_color = "#ffffff"
    line_color = "#222222"

    ax.set_facecolor(pitch_color)

    # Outer boundaries and halfway line
    ax.add_patch(Rectangle((0, 0), PITCH_LENGTH, PITCH_WIDTH, fill=False, color=line_color))
    ax.plot([PITCH_LENGTH / 2, PITCH_LENGTH / 2], [0, PITCH_WIDTH], color=line_color)

    # Penalty areas
    ax.add_patch(Rectangle((0, 18), 18, 44, fill=False, color=line_color))
    ax.add_patch(Rectangle((102, 18), 18, 44, fill=False, color=line_color))

    # Six-yard boxes
    ax.add_patch(Rectangle((0, 30), 6, 20, fill=False, color=line_color))
    ax.add_patch(Rectangle((114, 30), 6, 20, fill=False, color=line_color))

    # Goals
    ax.add_patch(Rectangle((-2, 36), 2, 8, fill=False, color=line_color))
    ax.add_patch(Rectangle((120, 36), 2, 8, fill=False, color=line_color))

    # Center circle and spots
    ax.add_patch(Circle((60, 40), 10, fill=False, color=line_color))
    ax.add_patch(Circle((60, 40), 0.8, color=line_color))
    ax.add_patch(Circle((12, 40), 0.8, color=line_color))
    ax.add_patch(Circle((108, 40), 0.8, color=line_color))

    # Penalty arcs
    ax.add_patch(Arc((12, 40), 20, 20, theta1=310, theta2=50, color=line_color))
    ax.add_patch(Arc((108, 40), 20, 20, theta1=130, theta2=230, color=line_color))

    ax.set_xlim(-3, PITCH_LENGTH + 3)
    ax.set_ylim(-3, PITCH_WIDTH + 3)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    return ax
