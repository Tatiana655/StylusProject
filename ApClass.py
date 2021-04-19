from PIL import Image, ImageTk
import tkinter as tk
import cv2
import numpy as np

import Paint
import ImgTransform
import Coord
import Definitions as Def

# объявление констант (Декорации)
NOTHING = "NOTHING"
READING = "READING"
MOVING = "MOVING"
DRAWING = "DRAWING"

# доступные режимы
MODE = {NOTHING: 0, READING: 1, MOVING: 2, DRAWING: 3}

ANY = Def.ANY
HAND = Def.HAND
READ_MODE = Def.READ_MODE

size = Def.size  # ребро квадрата-считывателя

# расположение квадрата
X = Def.X
Y = Def.Y
SHIFT = Def.SHIFT

# переменные для параметризации кода
PRINT = Def.PRINT
READ = Def.READ


class Application:
    # состояние системы (Главные действующие лица)
    cur_mode = MODE[NOTHING]  # екуущий режим
    cur_calib = READ_MODE[ANY]
    count_click = 0  # количество кликов для читалки (цвета с квадрата)
    coef_data = [3, 3, 3]  # blur_coef - 0  # open_coef - 1 # close_coef - 2 # всегда нечётные
    min_color = [255, 255, 255]  # bgr
    max_color = [0, 0, 0]  # bgr
    button = []  # кнопки сисетмы-приложения
    scroll = []  # скроллы калибровки
    label = []  # лэйблы кнопок (удивительно, но они и правда существуют отдельно)
    filter_point = []  # это картинка, которая хранит рисонок
    info_label = []  # поясняющие лэйблы

    # создание внутренних полей класса и виджетов (Второстепенные персонажи)
    # Ну и конечно же запуск петли:D
    def __init__(self):
        """ Initialize application which uses OpenCV + Tkinter. It displays
            a video stream in a Tkinter window and stores current snapshot on disk """
        self.vs = cv2.VideoCapture(0)  # capture video frames, 0 is your default video camera
        # self.output_path = output_path  # store output path
        self.current_image = None  # current image from the camera
        ok, frame = self.vs.read()  # reading opencv
        Application.filter_point = np.zeros_like(frame)  # start saving picture

        self.root = tk.Tk()  # initialize root window
        self.root.geometry("910x600")  # size of window
        self.root.title("gamma")  # set window title
        # self.destructor function gets fired when the window is closed
        self.root.protocol('WM_DELETE_WINDOW', self.destructor)  # destroy behavior

        self.panel = tk.Label(self.root)  # initialize image panel
        self.panel.pack(padx=10, pady=10, side='left')  # show panel

        # size of window display
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # create a buttons and remembering they in list-button, that when pressed the command is called
        btn_start = tk.Button(self.root, text="Click to START", font=100, command=self.reading)
        btn_start.pack(padx=10, pady=10, ipadx=900, ipady=600)  # show BIG START button
        Application.button.append(btn_start)
        Application.button.append(
            tk.Button(self.root, text="CLICK ME!", command=self.counting))  # сччтает клики СLICK_ME
        Application.button.append(tk.Button(self.root, text="NEXT",
                                            command=self.moving))
        Application.button.append(
            tk.Button(self.root, text="RESTART", command=self.reading))  # меняет состояние на чтение-калибровку
        Application.button.append(tk.Button(self.root, text="CHANGE_CALIB", command=self.change_calib))

        # create a scrolls and labels-scrolls
        Application.scroll.append(tk.Scale(self.root, length=255, orient='horizontal', from_=0, to=255))
        Application.label.append(tk.Label(self.root, text="b_min"))

        Application.scroll.append(tk.Scale(self.root, length=255, orient='horizontal', from_=0, to=255))
        Application.label.append(tk.Label(self.root, text="g_min"))

        Application.scroll.append(tk.Scale(self.root, length=255, orient='horizontal', from_=0, to=255))
        Application.label.append(tk.Label(self.root, text="r_min"))

        Application.scroll.append(tk.Scale(self.root, length=255, orient='horizontal', from_=0, to=255))
        Application.label.append(tk.Label(self.root, text="b_max"))

        Application.scroll.append(tk.Scale(self.root, length=255, orient='horizontal', from_=0, to=255))
        Application.label.append(tk.Label(self.root, text="g_max"))

        Application.scroll.append(tk.Scale(self.root, length=255, orient='horizontal', from_=0, to=255))
        Application.label.append(tk.Label(self.root, text="r_max"))

        Application.scroll.append(tk.Scale(self.root, length=255, orient='horizontal', from_=1, to=50))
        Application.label.append(tk.Label(self.root, text="blur_coef"))

        Application.scroll.append(tk.Scale(self.root, length=255, orient='horizontal', from_=1, to=50))
        Application.label.append(tk.Label(self.root, text="coef_rect_in"))

        Application.scroll.append(tk.Scale(self.root, length=255, orient='horizontal', from_=1, to=50))
        Application.label.append(tk.Label(self.root, text="coef_rect_out"))

        # inform labels
        Application.info_label.append(tk.Label(self.root,
                                               text="Place the marker object\nin the area of the square\n "
                                                    "and click the button.\n"
                                                    "SRUARE changes position\n(12 button clicks)",
                                               font=20))
        Application.info_label.append(tk.Label(self.root,
                                               text="Put your hand\n(mb in the glove)\nin the area of the squares\n "
                                                    "and click the button.\n(1 button click)",
                                               font=20))
        # инит пэинта
        self.paint = Paint.Paint()
        self.paint.init(self.root)
        # start a self.video_loop that constantly pools the video sensor
        # for the most recently read frame
        self.video_loop()

    # собственно вот и петля (работа с видеопотоком)
    def video_loop(self):
        """ Get frame from the video stream and show it in Tkinter """
        ok, frame = self.vs.read()  # read frame from video stream

        if ok:  # frame captured without any errors
            frame = cv2.flip(frame, 1)
            filter = np.zeros_like(frame)
            # рисовани квадратов, потом настройка скроллами
            if Application.cur_mode == MODE[READING]:
                # рисование квадратов
                if Application.cur_calib == READ_MODE[ANY]:
                    frame = ImgTransform.do_any(PRINT, frame)

                if Application.cur_calib == READ_MODE[HAND]:
                    if Application.count_click < 12:
                        frame = ImgTransform.do_hand(PRINT, frame)

                # доп настройка со скроллами
                if Application.count_click == 12:
                    Application.min_color = [Application.scroll[0].get(), Application.scroll[1].get(),
                                             Application.scroll[2].get()]
                    Application.max_color = [Application.scroll[3].get(), Application.scroll[4].get(),
                                             Application.scroll[5].get()]
                    Application.coef_data = [Application.scroll[6].get(), Application.scroll[7].get(),
                                             Application.scroll[8].get()]
                    # приметение фильтров
                    filter = ImgTransform.get_filtered_img(frame)
                    # получение актуальных координат точки-маркера
                    x, y = Coord.get_coord(filter, Application.cur_calib)
                    if (x != -1) and (y != -1):
                        filter = cv2.circle(filter, (x, y), 5, 100, -1)
                    frame = filter

            # "Рисование"
            if Application.cur_mode == MODE[MOVING]:
                # применение фильтров
                filter = ImgTransform.get_filtered_img(frame)
                # Самый главный экшен, который тут только может быть (рисование)
                x, y = Coord.get_coord(filter, Application.cur_calib)
                if (x != -1) and (y != -1):
                    Application.filter_point = cv2.circle(Application.filter_point, (x, y), self.paint.get_size(),
                                                          self.paint.get_color(), -1)

                frame = cv2.add(frame, Application.filter_point)

            # формирование отображаемой картинки
            if Application.cur_mode == MODE[READING] and Application.count_click == 12:
                # в режиме настройки покаывает, что видит фильтр
                # показвает достаточно ли хорошо ослеп

                cv2image = cv2.cvtColor(cv2.bitwise_and(frame, frame, mask=filter), cv2.COLOR_BGR2RGBA)
            else:
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)  # convert colors from BGR to RGBA

            # перевод координат ЦВЕТА и рисование в окно
            self.current_image = Image.fromarray(cv2image)  # convert image for PIL
            imgtk = ImageTk.PhotoImage(image=self.current_image)  # convert image for tkinter
            self.panel.imgtk = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            if Application.cur_mode != MODE[NOTHING]:
                self.panel.config(image=imgtk)  # show the image

        # и снова по новой
        self.root.after(30, self.video_loop)  # call the same function after 30 milliseconds

    # Тут изменение системы для отображения пэинта.
    # Этот метод даёт команду системе:
    # забудь всё что было и нарисуй мне пэинт
    def moving(self):
        Application.cur_mode = MODE[MOVING]
        Application.button[1].pack_forget()
        Application.button[2].pack_forget()
        Application.button[4].pack_forget()
        Application.info_label[0].pack_forget()
        Application.info_label[1].pack_forget()
        Application.button[3].pack(padx=10, pady=10)

        for s in Application.scroll:
            s.pack_forget()
        for lab in Application.label:
            lab.pack_forget()
        self.paint.show_buts()

    # считывание диапазона цветов с картинки, согл. режиму и включение доп. настройки со скроллами
    def counting(self):
        Application.count_click += 1
        ok, frame = self.vs.read()
        frame = cv2.flip(frame, 1)
        # цветовая читалка
        # читалка для 4 квадратов
        if Application.cur_calib == READ_MODE[ANY]:
            ImgTransform.do_any(READ, frame)

        # читалка для руки
        if Application.cur_calib == READ_MODE[HAND]:
            ImgTransform.do_hand(READ, frame)
            Application.count_click = 12

        # доп настройка фильтров скроллами
        # отобрази скроллы
        if Application.count_click == 12:
            for i in range(3):
                Application.scroll[i].set(Application.min_color[i])
                Application.scroll[i + 3].set(Application.max_color[i])
                Application.scroll[i + 6].set(Application.coef_data[i])
            for i in range(len(Application.scroll)):
                Application.label[i].pack()
                Application.scroll[i].pack()
            Application.button[2].pack(side='left', padx=1, pady=1)

            Application.button[1].pack_forget()
            Application.info_label[0].pack_forget()
            Application.info_label[1].pack_forget()
            Application.button[4].pack_forget()

    # Тут изменение системы для отображения квадратов-читальщиков
    def reading(self):
        Application.cur_mode = MODE[READING]
        Application.count_click = 0
        Application.button[1].pack(side='top', padx=10, pady=10)
        Application.button[4].pack(side='top', padx=10, pady=10)

        if Application.cur_calib == READ_MODE[ANY]:
            Application.info_label[1].pack_forget()
            Application.info_label[0].pack(side="left")

        if Application.cur_calib == READ_MODE[HAND]:
            Application.info_label[0].pack_forget()
            Application.info_label[1].pack(side="left")

        Application.button[0].pack_forget()
        Application.button[2].pack_forget()
        Application.button[3].pack_forget()
        self.paint.hide_buts()

        for s in Application.scroll:
            s.pack_forget()
        for lab in Application.label:
            lab.pack_forget()

    # Тут изменение системы для отображения конкретного вида квадратов-читальщиков
    @staticmethod
    def change_calib():
        if Application.cur_calib == READ_MODE[ANY]:
            Application.cur_calib = READ_MODE[HAND]
        else:
            Application.cur_calib = READ_MODE[ANY]

        if Application.cur_calib == READ_MODE[ANY]:
            Application.info_label[1].pack_forget()
            Application.info_label[0].pack(side="left")

        if Application.cur_calib == READ_MODE[HAND]:
            Application.info_label[0].pack_forget()
            Application.info_label[1].pack(side="left")

    # Тут изменение системы для того чтобы всё закончилось хорошо (все умерли в один день (и за один раз))
    def destructor(self):
        """ Destroy the root object and release all resources """
        # освободить ресурсы
        for s in Application.scroll:
            s.destroy()
        for b in Application.button:
            b.destroy()
        for lab in Application.label:
            lab.destroy()
        for info in Application.info_label:
            info.destroy()

        self.paint.destructor()

        #print("[INFO] closing...")
        self.root.destroy()
        self.vs.release()  # release web camera
        cv2.destroyAllWindows()

# go to Coord.py
