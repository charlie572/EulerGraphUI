from collections import Counter
from math import atan, cos, sin, degrees, sqrt

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


def get_bisector(point1, point2):
    if point1.y() == point2.y():
        m_2 = 9999999
    elif point1.x() == point2.x():
        m_2 = 0
    else:
        m_1 = (point1.y() - point2.y()) / (point1.x() - point2.x())
        m_2 = -1 / m_1

    centre = (point1 + point2) / 2
    c = centre.y() - m_2 * centre.x()

    return m_2, c


def get_line_intersection(m_1, c_1, m_2, c_2):
    if m_1 == m_2:
        return None

    x = (c_2 - c_1) / (m_1 - m_2)
    y = m_1 * x + c_1
    return QtCore.QPointF(x, y)


def get_circle(point1, point2, point3):
    m_1, c_1 = get_bisector(point1, point2)
    m_2, c_2 = get_bisector(point2, point3)

    centre = get_line_intersection(m_1, c_1, m_2, c_2)
    radius = sqrt((point1.x() - centre.x()) ** 2 + (point1.y() - centre.y()) ** 2)

    return centre, radius


def draw_arc_through_points(point1, point2, point3, painter):
    """Draw an arc through the given points in the given order

    :param point1: First point
    :type point1: QPoint
    :param point2: Second point
    :type point2: QPoint
    :param point3: Third point
    :type point3: QPoint
    :param painter: The painter to draw the arc
    :type painter: QPainter
    """
    # boundary rectangle (find a circle through all three points and then create a rectangle around the circle)
    centre, radius = get_circle(point1, point2, point3)
    rect = QtCore.QRect(int(centre.x() - radius), int(centre.y() - radius), 2 * int(radius), 2 * int(radius))

    # find the angles on the circle where the three points are (degrees anticlockwise from the positive x axis)
    angles = []
    for point in [point1, point2, point3]:
        if point.x() == centre.x():
            if point.y() < centre.y():
                angle = 90
            else:
                angle = 270
        else:
            angle = degrees(atan((centre.y() - point.y()) / (point.x() - centre.x())))

        if point.x() < centre.x():
            angle += 180

        if angle < 0:
            angle += 360

        angles.append(angle)

    # find the start angle and the arc length
    min_end = min(angles[0], angles[2])
    max_end = max(angles[0], angles[2])
    if min_end < angles[1] < max_end:
        start_angle = min_end
        arc_length = max_end - start_angle
    else:
        start_angle = max_end
        arc_length = 360 - start_angle + min_end

    # convert the angles to sixteenths of a degree (the format required by Qt)
    start_angle = int(start_angle) * 16
    arc_length = int(arc_length) * 16

    painter.drawArc(rect, start_angle, arc_length)


class EulerGraphWidget(QtWidgets.QWidget):
    def __init__(self, graph, *args, default_node_size=20, default_node_color=Qt.black, hover_colour=Qt.blue,
                 select_colour=Qt.red, zoom_rate=0.01, loop_width=20, loop_height=30, multi_edge_spacing=20, **kwargs):
        super(EulerGraphWidget, self).__init__(*args, **kwargs)

        self.default_node_size = default_node_size
        self.default_node_color = default_node_color
        self.hover_color = hover_colour
        self.select_colour = select_colour
        self.loop_width = loop_width
        self.loop_height = loop_height
        self.multi_edge_spacing = multi_edge_spacing

        self.zoom_rate = zoom_rate

        self.setMouseTracking(True)  # trigger mouse move events without clicking the mouse
        self.setFocusPolicy(Qt.ClickFocus)

        self.graph = graph
        self.next_node_id = 0
        while self.next_node_id in self.graph.nodes:
            self.next_node_id += 1

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
            self.createNode(event.x(), event.y())
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
                self.clearSelection()

            if event.modifiers() == Qt.AltModifier:
                # edge creation
                if self.drawing_edge:
                    end_node = self.hovered_node
                    start_node = self.edge_start_node

                    if end_node is not None:
                        self.addEdge(start_node, end_node)

                    self.edge_start_node = None
                    self.drawing_edge = False
            elif event.modifiers() == Qt.NoModifier or event.modifiers() == Qt.ControlModifier:
                # node and edge selection
                if self.node_being_selected is not None and self.node_being_selected == self.hovered_node:
                    self.selected_nodes.add(self.node_being_selected)
                elif self.edge_being_selected is not None and self.edge_being_selected == self.hovered_edge:
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
        self.hovered_node = None
        self.hovered_edge = None
        for node, data in self.graph.nodes().data():
            x, y, size, *_ = data.values()

            if point_circle_intersect(event.pos(), x, y, size):
                self.hovered_node = node
                break
        else:
            # check if the mouse is hovering over any edges (this will only run if the mouse isn't hovering over any
            # nodes)
            for start_node, end_node in self.graph.edges():
                if start_node != end_node:
                    # regular edge
                    line_x1 = self.graph.nodes[start_node]["x"]
                    line_y1 = self.graph.nodes[start_node]["y"]
                    line_x2 = self.graph.nodes[end_node]["x"]
                    line_y2 = self.graph.nodes[end_node]["y"]

                    if point_line_intersect(event.pos(), line_x1, line_y1, line_x2, line_y2):
                        self.hovered_edge = (start_node, end_node)
                        break
                else:
                    # loop
                    x = self.graph.nodes[start_node]["x"]
                    y = self.graph.nodes[start_node]["y"]

                    rect = QtCore.QRect(x - self.loop_width // 2, y, self.loop_width, self.loop_height)
                    if rect.contains(event.pos()):
                        self.hovered_edge = (start_node, end_node)
                        break
            else:
                self.hovered_edge = None

        # panning and moving selected nodes
        if self.panning:
            for node, data in self.graph.nodes().data():
                data["x"] += self.mouse_x - last_mouse_x
                data["y"] += self.mouse_y - last_mouse_y
        elif self.moving_nodes:
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

            self.clearSelection()

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
        edge_count = Counter()  # keeps track of the number of edges encountered between each node pair
        painter.setBrush(QtGui.QBrush(Qt.NoBrush))
        for start_node, end_node in self.graph.edges():
            # update and access the edge counter
            edge_count.update([(start_node, end_node)])
            edge_number = edge_count[start_node, end_node] - 1

            start_x = self.graph.nodes[start_node]["x"]
            start_y = self.graph.nodes[start_node]["y"]
            end_x = self.graph.nodes[end_node]["x"]
            end_y = self.graph.nodes[end_node]["y"]

            # style the edge
            if self.hovered_edge == (start_node, end_node):
                painter.setPen(hover_pen)
            elif (start_node, end_node) in self.selected_edges:
                painter.setPen(select_pen)
            else:
                painter.setPen(normal_pen)

            # draw the edge
            if start_node != end_node:
                if edge_number == 0:
                    # straight line
                    painter.drawLine(start_x, start_y, end_x, end_y)
                else:
                    # curved line

                    # calculate offset distance, which determines how far the curve is from the line
                    offset_distance = (edge_number + 1) // 2 * self.multi_edge_spacing

                    # calculate an offset vector from the straight line
                    line_centre = QtCore.QPointF((start_x + end_x) / 2, (start_y + end_y) / 2)

                    if start_y != end_y:
                        angle = atan(-(start_x - end_x) / (start_y - end_y))
                        offset = QtCore.QPointF(cos(angle) * offset_distance, sin(angle) * offset_distance)
                    else:
                        offset = QtCore.QPointF(0, -offset_distance)

                    # Add or subtract the offset vector to the centre point of the line. Alternate between adding and
                    # subtracting so that the edges will alternate above and below the line.
                    if edge_number % 2 == 0:
                        curve_point = line_centre + offset
                    else:
                        curve_point = line_centre - offset

                    # create integer point objects
                    start_point = QtCore.QPoint(start_x, start_y)
                    end_point = QtCore.QPoint(end_x, end_y)
                    curve_point = QtCore.QPoint(int(curve_point.x()), int(curve_point.y()))

                    # draw the curve between the nodes through the calculated point
                    draw_arc_through_points(start_point, curve_point, end_point, painter)
            else:
                # loop
                painter.drawEllipse(start_x - self.loop_width // 2, start_y, self.loop_width, self.loop_height)

        # draw an edge (when the user clicks and drags)
        if self.drawing_edge:
            painter.setPen(normal_pen)
            start_node = self.graph.nodes[self.edge_start_node]
            painter.drawLine(self.mouse_x, self.mouse_y, start_node["x"], start_node["y"])

        painter.end()

    def clearSelection(self):
        self.selected_nodes.clear()
        self.selected_edges.clear()

    def createNode(self, x, y, size=None, color=None):
        if size is None:
            size = self.default_node_size

        if color is None:
            color = self.default_node_color

        self.graph.add_node(self.next_node_id, x=x, y=y, size=size, color=color)
        self.hovered_node = self.next_node_id
        self.next_node_id += 1

    def addEdge(self, start_node, end_node):
        self.graph.add_edge(start_node, end_node)


def main():
    class Window(QtWidgets.QMainWindow):
        def __init__(self, *args, **kwargs):
            super(Window, self).__init__(*args, **kwargs)

            graph_widget = EulerGraphWidget(nx.MultiGraph(), self)
            self.setCentralWidget(graph_widget)
            self.setGeometry(0, 0, 480, 360)

    app = QtWidgets.QApplication([])

    window = Window()
    window.show()

    app.exec_()


if __name__ == "__main__":
    main()
