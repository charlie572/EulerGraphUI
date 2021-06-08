from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import networkx as nx


def between(value, boundary_1, boundary_2):
    if boundary_1 < boundary_2:
        return boundary_1 <= value <= boundary_2
    else:
        return boundary_2 <= value <= boundary_1


def point_circle_intersect(point, circle_x, circle_y, circle_diameter):
    return circle_x - circle_diameter // 2 <= point.x() <= circle_x + circle_diameter // 2 and \
           circle_y - circle_diameter // 2 <= point.y() <= circle_y + circle_diameter // 2


def point_line_intersect(point, line_x1, line_y1, line_x2, line_y2, min_distance=5):
    # the given line
    m_1 = (line_y1 - line_y2) / (line_x1 - line_x2)
    c_1 = line_y1 - m_1 * line_x1

    # perpendicular line passing through the point
    m_2 = -1 / m_1
    c_2 = point.y() - m_2 * point.x()

    # intersection of these lines
    intersection_x = (c_2 - c_1) / (m_1 - m_2)
    intersection_y = m_1 * intersection_x + c_1

    # if the line doesn't intersect the line segment, then check how close the point is to the ends of the line segment
    if not between(intersection_x, line_x1, line_x2):
        squared_distance_1 = (point.x() - line_x1) ** 2 + (point.y() - line_y1) ** 2
        squared_distance_2 = (point.x() - line_x2) ** 2 + (point.y() - line_y2) ** 2

        return squared_distance_1 < min_distance ** 2 or squared_distance_2 < min_distance ** 2

    # squared distance from the point to the line
    squared_distance = (point.x() - intersection_x) ** 2 + (point.y() - intersection_y) ** 2

    return squared_distance <= min_distance ** 2


class EulerGraphWidget(QtWidgets.QWidget):
    def __init__(self, *args, default_node_size=20, default_node_color=Qt.black, hover_colour=Qt.blue,
                 select_colour=Qt.red, zoom_rate=0.01, **kwargs):
        super(EulerGraphWidget, self).__init__(*args, **kwargs)

        self.default_node_size = default_node_size
        self.default_node_color = default_node_color
        self.hover_color = hover_colour
        self.select_colour = select_colour

        self.zoom_rate = zoom_rate

        self.setMouseTracking(True)  # trigger mouse move events without clicking the mouse
        self.setFocusPolicy(Qt.ClickFocus)

        self.graph = nx.Graph()
        self.next_node_id = 0

        # state

        self.mouse_x = None
        self.mouse_y = None

        self.hovered_node = None
        self.hovered_edge = None
        self.selected_nodes = set()
        self.selected_edges = set()
        self.node_being_selected = None
        self.edge_being_selected = None

        self.moving_nodes = False

        self.panning = False

        # these variables are used when the user clicks and drags to draw an edge
        self.drawing_edge = False
        self.edge_start_node = None

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton and event.modifiers() == Qt.ShiftModifier:
            self.create_node(event.x(), event.y())
        elif event.button() == Qt.LeftButton:
            # start selecting the hovered node
            self.node_being_selected = self.hovered_node
            self.edge_being_selected = self.hovered_edge

            if event.modifiers() == Qt.AltModifier:
                # start drawing an edge if the mouse is hovering over a node
                self.edge_start_node = self.hovered_node
                if self.edge_start_node is not None:
                    self.drawing_edge = True
            elif event.modifiers() == Qt.ShiftModifier:
                # start moving nodes if the mouse is hovering over a node
                if self.hovered_node is not None:
                    self.moving_nodes = True
        elif event.button() == Qt.MiddleButton:
            self.panning = True

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.moving_nodes = False

            if event.modifiers() != Qt.ControlModifier:
                self.clear_selection()

            if event.modifiers() == Qt.AltModifier:
                if self.drawing_edge:
                    # finish drawing the edge
                    end_node = self.hovered_node
                    start_node = self.edge_start_node

                    if end_node is not None and not self.graph.has_edge(start_node, end_node) and \
                            end_node != start_node:
                        self.add_edge(start_node, end_node)

                    self.edge_start_node = None
                    self.drawing_edge = False

            if self.node_being_selected is not None and self.node_being_selected == self.hovered_node:
                # select this node
                self.selected_nodes.add(self.node_being_selected)
            elif self.edge_being_selected is not None and self.edge_being_selected == self.hovered_edge:
                # select this edge
                self.selected_edges.add(self.edge_being_selected)

            self.node_being_selected = None
            self.edge_being_selected = None
        elif event.button() == Qt.MiddleButton:
            self.panning = False

        self.update()

    def mouseMoveEvent(self, event):
        last_mouse_x = self.mouse_x
        last_mouse_y = self.mouse_y
        self.mouse_x = event.x()
        self.mouse_y = event.y()

        # check if the mouse is hovering over any nodes
        for node, data in self.graph.nodes().data():
            x, y, size, *_ = data.values()

            if point_circle_intersect(event.pos(), x, y, size):
                self.hovered_node = node
                break
        else:
            self.hovered_node = None

            # check if the mouse is hovering over any edges
            for start_node, end_node in self.graph.edges():
                line_x1 = self.graph.nodes[start_node]["x"]
                line_y1 = self.graph.nodes[start_node]["y"]
                line_x2 = self.graph.nodes[end_node]["x"]
                line_y2 = self.graph.nodes[end_node]["y"]

                if point_line_intersect(event.pos(), line_x1, line_y1, line_x2, line_y2):
                    self.hovered_edge = (start_node, end_node)
                    break
            else:
                self.hovered_edge = None

        if self.panning:
            # pan
            for node, data in self.graph.nodes().data():
                data["x"] += self.mouse_x - last_mouse_x
                data["y"] += self.mouse_y - last_mouse_y
        elif self.moving_nodes:
            # move selected nodes
            for node in self.selected_nodes:
                self.graph.nodes[node]["x"] += self.mouse_x - last_mouse_x
                self.graph.nodes[node]["y"] += self.mouse_y - last_mouse_y

        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            # delete nodes and edges
            for node in self.selected_nodes:
                self.graph.remove_node(node)

            for edge in self.selected_edges:
                if self.graph.has_edge(*edge):
                    self.graph.remove_edge(*edge)

            self.clear_selection()

        self.update()

    def wheelEvent(self, event):
        # zoom

        # calculate scale factor
        if event.angleDelta().y() > 0:
            # zoom in
            scale_factor = event.angleDelta().y() * self.zoom_rate
        else:
            # zoom out
            scale_factor = -1 / (event.angleDelta().y() * self.zoom_rate)

        # multiply all positions by the scale factor
        for node, data in self.graph.nodes().data():
            data["x"] = int((data["x"] - self.mouse_x) * scale_factor + self.mouse_x)
            data["y"] = int((data["y"] - self.mouse_y) * scale_factor + self.mouse_y)

        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        # pen styles
        hover_pen = QtGui.QPen()
        hover_pen.setWidth(2)
        hover_pen.setColor(self.hover_color)

        select_pen = QtGui.QPen()
        select_pen.setWidth(2)
        select_pen.setColor(self.select_colour)

        no_pen = QtGui.QPen()
        no_pen.setStyle(Qt.NoPen)

        normal_pen = QtGui.QPen()

        # draw nodes
        for node, data in self.graph.nodes().data():
            x, y, size, color, *_ = data.values()

            # style the fill
            painter.setBrush(QtGui.QBrush(color, Qt.SolidPattern))

            # style the outline
            if self.hovered_node == node:
                painter.setPen(hover_pen)
            elif node in self.selected_nodes:
                painter.setPen(select_pen)
            else:
                painter.setPen(no_pen)

            painter.drawEllipse(x - size // 2, y - size // 2, size, size)

        # draw edges
        for start_node, end_node in self.graph.edges():
            start_x = self.graph.nodes[start_node]["x"]
            start_y = self.graph.nodes[start_node]["y"]
            end_x = self.graph.nodes[end_node]["x"]
            end_y = self.graph.nodes[end_node]["y"]

            # style the line
            if self.hovered_edge == (start_node, end_node):
                painter.setPen(hover_pen)
            elif (start_node, end_node) in self.selected_edges:
                painter.setPen(select_pen)
            else:
                painter.setPen(normal_pen)

            painter.drawLine(start_x, start_y, end_x, end_y)

        # draw an edge (when the user clicks and drags)
        if self.drawing_edge:
            painter.setPen(normal_pen)
            start_node = self.graph.nodes[self.edge_start_node]
            painter.drawLine(self.mouse_x, self.mouse_y, start_node["x"], start_node["y"])

        painter.end()

    def clear_selection(self):
        self.selected_nodes.clear()
        self.selected_edges.clear()

    def create_node(self, x, y, size=None, color=None):
        if size is None:
            size = self.default_node_size

        if color is None:
            color = self.default_node_color

        self.graph.add_node(self.next_node_id, x=x, y=y, size=size, color=color)
        self.hovered_node = self.next_node_id
        self.next_node_id += 1

    def add_edge(self, start_node, end_node):
        self.graph.add_edge(start_node, end_node)


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
