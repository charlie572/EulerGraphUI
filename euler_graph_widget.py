from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import networkx as nx


class EulerGraphWidget(QtWidgets.QWidget):
    def __init__(self, *args, default_node_size=20, default_node_color=Qt.black, **kwargs):
        super(EulerGraphWidget, self).__init__(*args, **kwargs)

        self.default_node_size = default_node_size
        self.default_node_color = default_node_color

        self.graph = nx.Graph()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton and event.modifiers() == Qt.ShiftModifier:
            # create node
            node_id = len(self.graph)
            self.graph.add_node(node_id, x=event.x(), y=event.y(),
                                         size=self.default_node_size,
                                         color=self.default_node_color)

            # invoke a paint event
            self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        # draw nodes
        for node, data in self.graph.nodes().data():
            x, y, size, color = data.values()

            painter.setBrush(QtGui.QBrush(color, Qt.SolidPattern))
            painter.drawEllipse(x - size//2, y - size//2, size, size)

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
