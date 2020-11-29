from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import time

IMG_BOMB = QImage("./img/bomb.png")
IMG_FLAG = QImage("./img/flag.png")
IMG_CLOCK = QImage("./img/clock.png")

NUM_COLORS = {
    1: QColor('#f44336'),
    2: QColor('#9C27B0'),
    3: QColor('#3F51B5'),
    4: QColor('#03A9F4')
}

STATUS_READY = 0
STATUS_PLAYING = 1
STATUS_FAILED = 2
STATUS_SUCCESS = 3

STATUS_ICONS = {
    0: "./img/smile.png",
    1: "./img/sad.png",
}


class Box(QWidget):
    expand_signal = pyqtSignal(int, int)
    click_signal = pyqtSignal()
    ko_signal = pyqtSignal()
    win_signal = pyqtSignal()

    def __init__(self, x, y, *args, **kwargs):
        super(Box, self).__init__(*args, **kwargs)
        self.setFixedSize(QSize(50, 50))

        self.x = x
        self.y = y

    def reset(self):
        self.num = 0
        self.is_bomb = False
        self.is_clicked = False
        self.is_flagged = False
        
        self.update()

    def paintEvent(self, event):
        # init painter
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # event region
        r = event.rect()

        if self.is_clicked:
            color = self.palette().color(QPalette.Background)
            outer, inner = Qt.gray, color
        else:
            outer, inner = Qt.gray, Qt.lightGray
        
        # set box fill
        p.fillRect(r, QBrush(inner))
        
        # set box border
        pen = QPen(outer)
        pen.setWidth(1)
        p.setPen(pen)
        p.drawRect(r)

        # set box icon
        if self.is_clicked:
            # set box bomb icon
            if self.is_bomb:
                p.drawPixmap(r, QPixmap(IMG_BOMB))

            # set box number
            elif self.num > 0:
                pen = QPen(NUM_COLORS[self.num])
                p.setPen(pen)
                f = p.font()
                f.setBold(True)
                p.setFont(f)
                p.drawText(r, Qt.AlignHCenter | Qt.AlignVCenter, str(self.num))

        # set box flag icon
        elif self.is_flagged:
            p.drawPixmap(r, QPixmap(IMG_FLAG))

    def flag(self):
        self.is_flagged = True
        self.update()

        self.click_signal.emit()

    def open(self):
        self.is_clicked = True
        self.update()

    def click(self):
        if not self.is_clicked:
            self.open()
            if self.num == 0:
                self.expand_signal.emit(self.x, self.y)
        self.click_signal.emit()

    def mouseReleaseEvent(self, e):
        if (e.button() == Qt.RightButton and not self.is_clicked):
            self.flag()
            # check win condition
            # num of flag equals to num of bomb
            # and flag(s) are placed correctly

        elif (e.button() == Qt.LeftButton):
            self.click()
            if self.is_bomb:
                self.ko_signal.emit()


class Board(QMainWindow):
    def __init__(self, board_size, n_bombs, arr_bombs, *args, **kwargs):
        super(Board, self).__init__(*args, **kwargs)

        self.board_size = board_size
        self.n_bombs = n_bombs
        self.arr_bombs = arr_bombs

        w = QWidget()
        hb = QHBoxLayout()

        self.bombs = QLabel()
        self.bombs.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        self.clock = QLabel()
        self.clock.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        f = self.bombs.font()
        f.setPointSize(24)
        f.setWeight(75)
        self.bombs.setFont(f)
        self.clock.setFont(f)

        self._timer = QTimer()
        self._timer.timeout.connect(self.update_timer)
        self._timer.start(1000)  # 1 second timer

        self.bombs.setText("%02d" % self.n_bombs)
        self.clock.setText("00")

        self.button = QPushButton()
        self.button.setFixedSize(QSize(50, 50))
        self.button.setIconSize(QSize(50, 50))
        self.button.setIcon(QIcon("./img/smiley.png"))
        self.button.setFlat(True)

        self.button.pressed.connect(self.button_pressed)

        l = QLabel()
        l.setPixmap(QPixmap.fromImage(IMG_BOMB))
        l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hb.addWidget(l)

        hb.addWidget(self.bombs)
        hb.addWidget(self.button)
        hb.addWidget(self.clock)

        l = QLabel()
        l.setPixmap(QPixmap.fromImage(IMG_CLOCK))
        l.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hb.addWidget(l)

        vb = QVBoxLayout()
        vb.addLayout(hb)

        self.grid = QGridLayout()
        self.grid.setSpacing(5)

        vb.addLayout(self.grid)
        w.setLayout(vb)
        self.setCentralWidget(w)

        self.init_map()
        self.update_status(STATUS_READY)

        self.reset_map()
        self.update_status(STATUS_READY)

        self.show()

    def init_map(self):
        # Add positions to the map
        for x in range(0, self.board_size):
            for y in range(0, self.board_size):
                w = Box(x, y)
                self.grid.addWidget(w, y, x)
                # Connect signal to handle expansion.
                w.click_signal.connect(self.trigger_start)
                w.expand_signal.connect(self.expand_reveal)
                w.ko_signal.connect(self.game_over)
                w.win_signal.connect(self.game_win)

    def reset_map(self):
        # Clear all bomb positions
        for x in range(0, self.board_size):
            for y in range(0, self.board_size):
                w = self.grid.itemAtPosition(y, x).widget()
                w.reset()

        # Add bombs to boxes on board
        for (x, y) in self.arr_bombs:
            if (x, y) != (0, 0):
                w = self.grid.itemAtPosition(y, x).widget()
                w.is_bomb = True

        def get_adjacency_n(x, y):
            coords = self.get_surrounding(x, y)
            n_bombs = sum(1 if w.is_bomb else 0 for w in coords)

            return n_bombs

        # Add adjacencies to the boxes on board
        for x in range(0, self.board_size):
            for y in range(0, self.board_size):
                w = self.grid.itemAtPosition(y, x).widget()
                w.num = get_adjacency_n(x, y)

        # Place starting click
        while True:
            (x, y) = (0, 0)

            # Reveal all positions around starting point, if they are not bombs.
            for w in self.get_surrounding(x, y):
                if not w.is_bomb:
                    w.click()
            break

    def get_surrounding(self, x, y):
        coords = []

        for xi in range(max(0, x - 1), min(x + 2, self.board_size)):
            for yi in range(max(0, y - 1), min(y + 2, self.board_size)):
                coords.append(self.grid.itemAtPosition(yi, xi).widget())

        return coords

    def button_pressed(self):
        if self.status == STATUS_PLAYING:
            self.update_status(STATUS_FAILED)
            self.reveal_map()

        elif self.status == STATUS_FAILED:
            self.update_status(STATUS_READY)
            self.reset_map()

    def reveal_map(self):
        for x in range(0, self.board_size):
            for y in range(0, self.board_size):
                w = self.grid.itemAtPosition(y, x).widget()
                w.open()

    def expand_reveal(self, x, y):
        for xi in range(max(0, x - 1), min(x + 2, self.board_size)):
            for yi in range(max(0, y - 1), min(y + 2, self.board_size)):
                w = self.grid.itemAtPosition(yi, xi).widget()
                if not w.is_bomb:
                    w.click()

    def trigger_start(self, *args):
        if self.status != STATUS_PLAYING:
            # First click
            self.update_status(STATUS_PLAYING)
            # Start timer
            self._timer_start_nsecs = int(time.time())

    def update_status(self, status):
        self.status = status
        if status == STATUS_FAILED:
            self.button.setIcon(QIcon(STATUS_ICONS[1]))
        else:
            self.button.setIcon(QIcon(STATUS_ICONS[0]))

    def update_timer(self):
        if self.status == STATUS_PLAYING:
            n_secs = int(time.time()) - self._timer_start_nsecs
            self.clock.setText("%02d" % n_secs)

    def game_over(self):
        self.reveal_map()
        self.update_status(STATUS_FAILED)

    def game_win(self):
        self.update_status(STATUS_SUCCESS)


if __name__ == '__main__':
    app = QApplication([])
    arr_bombs = [(0,1), (1,1), (2,3), (3,3), (4,4)]
    print(arr_bombs)
    for i in arr_bombs:
        print(i)
    window = Board(5, 5, arr_bombs)
    app.exec_()