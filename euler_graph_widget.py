from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import networkx as nx


def point_circle_intersect(point, circle_x, circle_y, circle_diameter):
    return circle_x - circle_diameter // 2 <= point.x() <= circle_x + circle_diameter // 2 and \
           circle_y - circle_diameter // 2 <= point.y() <= circle_y + circle_diameter // 2


class EulerGraphWidget(QtWidgets.QWidget):
    def __init__(self, *args, default_node_size=20, default_node_color=Qt.black, hover_colour=Qt.blue, **kwargs):
        super(EulerGraphWidget, self).__init__(*args, **kwargs)

        self.default_node_size = default_node_size
        self.default_node_color = default_node_color
        self.hover_color = hover_colour

        self.setMouseTracking(True)

        self.graph = nx.Graph()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton and event.modifiers() == Qt.ShiftModifier:
            # create node
            node_id = len(self.graph)
            self.graph.add_node(node_id, x=event.x(), y=event.y(),
                                size=self.default_node_size,
                                color=self.default_node_color,
                                hovering=True)

            # invoke a paint event
            self.update()

    def mouseMoveEvent(self, event):
        # check if the mouse is hovering over any nodes
        for node, data in self.graph.nodes().data():
            x, y, size, *_ = data.values()

            data["hovering"] = point_circle_intersect(event.pos(), x, y, size)

        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        # pen styles
        hover_pen = QtGui.QPen()
        hover_pen.setWidth(2)
        hover_pen.setColor(self.hover_color)

        normal_pen = QtGui.QPen()
        normal_pen.setStyle(Qt.NoPen)

        # draw nodes
        for node, data in self.graph.nodes().data():
            x, y, size, color, hovering, *_ = data.values()

            # style the fill
            painter.setBrush(QtGui.QBrush(color, Qt.SolidPattern))

            # style the outline
            if hovering:
                painter.setPen(hover_pen)
            else:
                painter.setPen(normal_pen)

            painter.drawEllipse(x - size // 2, y - size // 2, size, size)

        painter.end()


def main():
    class Window(QtWidgets.QMainWindow):
        def __init__(self, *args, **kwargs):
            super(Window, self).__init__(*args, **kwargs)

            graph_widget = EulerGraphWidget(self)
            self.setCentralWidget(graph_widget)
            self.setGeometry(0, 0, 480, 360)

    app = QtWidgets.QApplication([])

    window = Window()
    window.show()

    app.exec_()


if __name__ == "__main__":
    main()
