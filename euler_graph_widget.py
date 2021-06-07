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

        # trigger mouse move events without clicking the mouse
        self.setMouseTracking(True)

        self.graph = nx.Graph()

        # state

        self.mouse_x = None
        self.mouse_y = None

        # these variables are used when the user clicks and drags to draw an edge
        self.drawing_edge = False
        self.edge_start_node = None

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton and event.modifiers() == Qt.ShiftModifier:
            # create node
            node_id = len(self.graph)
            self.graph.add_node(node_id, x=event.x(), y=event.y(),
                                size=self.default_node_size,
                                color=self.default_node_color,
                                hovering=True)
        elif event.button() == Qt.LeftButton and event.modifiers() == Qt.NoModifier:
            # start drawing an edge if the mouse is hovering over a node
            self.edge_start_node = self.get_hovered_node()
            if self.edge_start_node is not None:
                self.drawing_edge = True

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing_edge:
            # finish drawing an edge
            end_node = self.get_hovered_node()
            if end_node is not None and not self.graph.has_edge(self.edge_start_node, end_node):
                self.graph.add_edge(self.edge_start_node, end_node)

            self.edge_start_node = None
            self.drawing_edge = False

        self.update()

    def mouseMoveEvent(self, event):
        self.mouse_x = event.x()
        self.mouse_y = event.y()

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

        no_pen = QtGui.QPen()
        no_pen.setStyle(Qt.NoPen)

        normal_pen = QtGui.QPen()

        # draw nodes
        for node, data in self.graph.nodes().data():
            x, y, size, color, hovering, *_ = data.values()

            # style the fill
            painter.setBrush(QtGui.QBrush(color, Qt.SolidPattern))

            # style the outline
            if hovering:
                painter.setPen(hover_pen)
            else:
                painter.setPen(no_pen)

            painter.drawEllipse(x - size // 2, y - size // 2, size, size)

        # draw edges
        painter.setPen(normal_pen)
        for start_node, end_node in self.graph.edges():
            start_x = self.graph.nodes[start_node]["x"]
            start_y = self.graph.nodes[start_node]["y"]
            end_x = self.graph.nodes[end_node]["x"]
            end_y = self.graph.nodes[end_node]["y"]

            painter.drawLine(start_x, start_y, end_x, end_y)

        # draw an edge (when the user clicks and drags)
        if self.drawing_edge:
            painter.setPen(normal_pen)
            start_node = self.graph.nodes[self.edge_start_node]
            painter.drawLine(self.mouse_x, self.mouse_y, start_node["x"], start_node["y"])

        painter.end()

    def get_hovered_node(self):
        for node, data in self.graph.nodes().data():
            if data["hovering"]:
                return node

        return None


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
