from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import networkx as nx


class EulerGraphWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(EulerGraphWidget, self).__init__(*args, **kwargs)


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
