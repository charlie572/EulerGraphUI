from collections import Counter
from math import atan, cos, sin, degrees, sqrt, radians, pi

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
        angles.append(get_angle(point.x() - centre.x(), centre.y() - point.y()))

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


def get_angle(x, y):
    if x == 0:
        if y > 0:
            angle = 90
        else:
            angle = 270
    else:
        angle = degrees(atan(y / x))

    if x < 0:
        angle += 180

    angle %= 360

    return angle


def num_edges(start_node, end_node, graph):
    result = 0
    for node1, node2 in graph.edges():
        if node1 == start_node and node2 == end_node:
            result += 1

    return result


class EulerGraphWidget(QtWidgets.QWidget):
    class BaseWidgetOnEdge(QtWidgets.QWidget):
        def __init__(self, edge, *args, **kwargs):
            super(EulerGraphWidget.BaseWidgetOnEdge, self).__init__(*args, **kwargs)

            self.setFixedWidth(20)
            self.setFixedHeight(20)

            self.edge = edge

            self.line_edit = QtWidgets.QLineEdit("1", self)
            self.line_edit.setFrame(False)
            self.line_edit.setAutoFillBackground(True)
            self.line_edit.setStyleSheet("""background-color: transparent;
                                            color: red;
                                            font-size: 15px""")

            # traverse all children depth first to install event filters
            stack = [self]
            while stack:
                widget = stack.pop()

                widget.installEventFilter(self)

                try:
                    widget.setMouseTracking(True)
                except AttributeError:
                    pass

                stack.extend(widget.children())

        def eventFilter(self, obj, event):
            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.parent().selectEdge(self.edge, event.modifiers() == Qt.ControlModifier)
            elif event.type() == QtCore.QEvent.MouseMove:
                self.parent().hoverEdge(self.edge)
            elif event.type() == QtCore.QEvent.KeyPress:
                if event.key() == Qt.Key_Delete:
                    self.parent().deleteSelection()

            return False

        def get_edge(self):
            return self.edge

    class BaseWidgetOnNode(QtWidgets.QWidget):
        def __init__(self, *args, **kwargs):
            super(EulerGraphWidget.BaseWidgetOnNode, self).__init__(*args, **kwargs)

            self.setFixedWidth(20)
            self.setFixedHeight(20)

    WidgetOnEdge = BaseWidgetOnEdge
    WidgetOnNode = BaseWidgetOnNode

    def __init__(self, graph, *args, default_node_size=20, default_node_color=Qt.black, hover_colour=Qt.blue,
                 select_colour=Qt.red, zoom_rate=0.01, loop_width=20, loop_height=30, multi_edge_spacing=20,
                 direction_triangle_size=15, default_edge_color=Qt.black, **kwargs):
        super(EulerGraphWidget, self).__init__(*args, **kwargs)

        self.default_node_size = default_node_size
        self.default_node_color = default_node_color
        self.default_edge_color = default_edge_color
        self.hover_color = hover_colour
        self.select_colour = select_colour
        self.loop_width = loop_width
        self.loop_height = loop_height
        self.multi_edge_spacing = multi_edge_spacing
        self.direction_triangle_size = direction_triangle_size
        self.direction_triangle_height = sqrt(direction_triangle_size ** 2 - (direction_triangle_size / 2) ** 2)

        self.directed = isinstance(graph, (nx.DiGraph, nx.MultiDiGraph)) or \
                        issubclass(type(graph), (nx.DiGraph, nx.MultiDiGraph))
        self.multi_edge = isinstance(graph, (nx.MultiGraph or nx.MultiDiGraph)) or \
                          issubclass(type(graph), (nx.MultiGraph or nx.MultiDiGraph))

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
            if event.modifiers() != Qt.ControlModifier:
                self.clearSelection()

            self.selected_nodes.add(self.hovered_node)

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

            if event.modifiers() == Qt.AltModifier:
                # edge creation
                if self.drawing_edge:
                    end_node = self.hovered_node
                    start_node = self.edge_start_node

                    if end_node is not None:
                        self.addEdge(start_node, end_node)

                    self.edge_start_node = None
                    self.drawing_edge = False
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
        for node, data in self.graph.nodes().data():
            x, y, size, *_ = data.values()

            if point_circle_intersect(event.pos(), x, y, size):
                self.hovered_node = node
                break

        # If this event is triggered, the mouse isn't over a child widget, so it cannot be hovering over an edge.
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
            self.deleteSelection()

    def wheelEvent(self, event):
        # zoom

        if event.angleDelta().y() != 0:
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

            # draw the node
            painter.drawEllipse(x - size // 2, y - size // 2, size, size)

            # move the widget
            widget = data["widget"]
            width = widget.width()
            height = widget.height()
            widget.move(x - width // 2, y - height - size // 2)

        # draw edges
        edge_count = Counter()  # keeps track of the number of edges encountered between each node pair
        painter.setBrush(QtGui.QBrush(Qt.NoBrush))

        for start_node, end_node, *_ in self.edges(data=True):
            data = _[-1]
            if len(_) == 2:
                key = _[0]
            else:
                key = None

            # update and access the edge counter
            edge_count.update([(start_node, end_node), (end_node, start_node)])
            edge_number = edge_count[start_node, end_node] - 1

            start_x = self.graph.nodes[start_node]["x"]
            start_y = self.graph.nodes[start_node]["y"]
            end_x = self.graph.nodes[end_node]["x"]
            end_y = self.graph.nodes[end_node]["y"]

            # style the edge
            if self.hovered_edge in [(start_node, end_node), (start_node, end_node, key)]:
                painter.setPen(hover_pen)
            elif (start_node, end_node) in self.selected_edges or (start_node, end_node, key) in self.selected_edges:
                painter.setPen(select_pen)
            else:
                painter.setPen(normal_pen)

            # draw the edge
            if start_node != end_node:
                if edge_number == 0:
                    # straight line
                    painter.drawLine(start_x, start_y, end_x, end_y)

                    if self.directed:
                        # draw triangle to show direction

                        # first point is in the centre of the line
                        line_centre = QtCore.QPointF((start_x + end_x) / 2, (start_y + end_y) / 2)

                        # get two perpendicular offset vectors
                        line_angle = radians(get_angle(end_x - start_x, start_y - end_y))

                        painter.setBrush(QtGui.QBrush(Qt.SolidPattern))
                        self._draw_direction_triangle(line_centre, line_angle, painter)

                    # move widget
                    widget = data["widget"]
                    width = widget.width()
                    height = widget.height()
                    widget.move((start_x + end_x) // 2 - width // 2, (start_y + end_y) // 2 - height // 2)
                else:
                    # curved line

                    # calculate offset distance, which determines how far the curve is from the line
                    offset_distance = (edge_number + 1) // 2 * self.multi_edge_spacing

                    # calculate an offset vector from the straight line
                    angle = radians(get_angle(end_x - start_x, start_y - end_y) + 90)
                    offset = QtCore.QPointF(cos(angle) * offset_distance, -sin(angle) * offset_distance)

                    # If the edge is going in the other direction, the offset needs to be flipped so the edge curves
                    # in the right direction.
                    if start_node < end_node:
                        offset *= -1

                    # Add or subtract the offset vector to the centre point of the line. Alternate between adding and
                    # subtracting so that the edges will alternate above and below the line.
                    line_centre = QtCore.QPointF((start_x + end_x) / 2, (start_y + end_y) / 2)
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

                    if self.directed:
                        # draw direction arrow
                        painter.setBrush(QtGui.QBrush(Qt.SolidPattern))
                        self._draw_direction_triangle(curve_point, angle - pi/2, painter)

                    # move spin box
                    widget = data["widget"]
                    width = widget.width()
                    height = widget.height()
                    widget.move(curve_point.x() - width // 2, curve_point.y() - height // 2)
            else:
                # loop
                painter.setBrush(QtGui.QBrush(Qt.NoBrush))
                painter.drawEllipse(start_x - self.loop_width // 2, start_y, self.loop_width, self.loop_height)

                # move widget
                widget = data["widget"]
                width = widget.width()
                height = widget.height()
                data["widget"].move(start_x - width // 2, start_y + self.loop_height - height // 2)

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

        widget = self.WidgetOnNode(self)
        widget.show()

        self.graph.add_node(self.next_node_id, x=x, y=y, size=size, color=color, widget=widget)

        self.hovered_node = self.next_node_id
        self.next_node_id += 1

    def addEdge(self, start_node, end_node, color=None):
        if color is None:
            color = self.default_edge_color

        if self.multi_edge:
            edge_num = num_edges(start_node, end_node, self.graph)
            if not self.directed:
                edge_num += num_edges(end_node, start_node, self.graph)

            edge = start_node, end_node, edge_num
        else:
            edge = start_node, end_node

        # widget on edge
        widget = self.WidgetOnEdge(edge, self)
        widget.show()

        self.graph.add_edge(start_node, end_node, widget=widget, color=color)

    def selectEdge(self, edge, multi_select=False):
        if not multi_select:
            self.clearSelection()

        self.selected_edges.add(edge)

        self.update()

    def hoverEdge(self, edge):
        self.hovered_edge = edge
        self.update()

    def deleteSelection(self):
        # delete nodes
        for node in self.selected_nodes:
            for edge in dict(self.graph.edges):
                if node == edge[0] or node == edge[1]:
                    self._delete_edge(edge)

            self.graph.remove_node(node)

        # delete edges
        for edge in self.selected_edges:
            self._delete_edge(edge)

        self.clearSelection()

        self.update()

    def setNodeColor(self, node, color):
        self.graph.nodes[node]["color"] = color

    def setEdgeColor(self, edge, color):
        self.graph.edges[edge]["color"] = color

    def edges(self, data=False):
        if self.multi_edge:
            return self.graph.edges(keys=True, data=data)
        else:
            return self.graph.edges(data=data)

    def nodes(self, data=False):
        return self.graph.nodes(data=data)

    def _draw_direction_triangle(self, point1, angle, painter):
        # calculate offset vector along and perpendicular to the line
        offset1 = -QtCore.QPointF(cos(angle) * self.direction_triangle_height,
                                  -sin(angle) * self.direction_triangle_height)
        offset2 = QtCore.QPointF(cos(angle + pi / 2) * self.direction_triangle_size / 2,
                                 -sin(angle + pi / 2) * self.direction_triangle_size / 2)

        # calculate other two points
        point2 = point1 + offset1 + offset2
        point3 = point1 + offset1 - offset2

        # draw the triangle
        painter.drawPolygon(point1, point2, point3)

    def _delete_edge(self, edge):
        if self.graph.has_edge(*edge):
            widget = self.graph.edges[edge]["widget"]
            widget.deleteLater()
            self.graph.remove_edge(*edge)


def main():
    class Window(QtWidgets.QMainWindow):
        def __init__(self, *args, **kwargs):
            super(Window, self).__init__(*args, **kwargs)

            graph_widget = EulerGraphWidget(nx.DiGraph(), self)
            self.setCentralWidget(graph_widget)
            self.setGeometry(0, 0, 480, 360)

    app = QtWidgets.QApplication([])

    window = Window()
    window.show()

    app.exec_()


if __name__ == "__main__":
    main()
