from tkinter import Tk, Toplevel, Frame, Label, Button, Entry, StringVar, NSEW, N, S, E, W, \
    Canvas, RIDGE, DISABLED, NORMAL, Scale, IntVar, HORIZONTAL, RAISED, SUNKEN
from tkinter import ttk
import os, platform
import re
import yaml
import random
import time
import requests
from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image, ImageTk

class GUI:
    def __init__(self):
        """Tkinter application class initialization
        :rtype: App class
        """
        self.network = None
        self.cur_lang = 'en'

        # init window
        self.tk = Tk()
        self.tk.grid()
        self.tk.protocol("WM_DELETE_WINDOW", lambda parent=self.tk: CustomDialog.quit_dialog(parent, self.cur_lang))
        self.tk.resizable(False, False)

        # main frame
        self.imgFrame = ImageFrame(self.tk)
        self.imgFrame.init_lang_action(self)
        self.experiment = Experiment(self)
        self.lock_buttons(True)
        self.__check_folders()
        self.is_loaded_survey = False

    def __check_folders(self):
        """
        Check if folders are existed
        """
        path = Path('images')
        if not path.exists():
            CustomDialog.noimage_dialog(self.tk, 'noimagetitle', 'noimagemessage')
        path = Path('results')
        if not path.exists():
            path.mkdir()

    def __begin_action(self):
        surveys = list(filter(os.path.isfile, Path('results').glob('*survey.yaml')))
        self.is_filling_survey = False
        if not surveys:
            # demo mode
            self.is_filling_survey = True
            self.__survey_dialog(self.tk)
            # self.imgFrame.tk.title(self.imgFrame.language[self.cur_lang]['title']+"[ demo ]")
        else:
            # if surveys:
            if self.experiment.mode != "demo":
                self.experiment.mode = 'full'
                self.imgFrame.configure({'name': {'text': YAML.read(surveys[0])['name']}})
            self.is_loaded_survey = True
            # self.experiment.mode = 'full'
            self.__start_experiment()

    def __survey_dialog(self, parent_tk):
        win = CustomDialog.survey_dialog(parent_tk)
        survey = SurveyFrame(win)
        survey.configure({'button': {'command': lambda: self.__survey_save(win, survey.get_data())}})
        # survey.set_button_action(lambda: self.__survey_save(win, survey.get_data()))

    def __survey_save(self, dialog, data: dict):
        """
        Create custom dialog windows for saving user experiments data to file
        :param dialog: parent window
        :param data: gathered data to save
        """
        if not data:
            CustomDialog.ok_dialog(dialog, 'survey', 'survey_mistake')
            # win.focus_set()
        else:
            YAML.write(data, f'{data["name"]}_survey.yaml', 'results')
            # Network.upload_file(data['name'], file_name, 'results')
            dialog.destroy()
            self.experiment.mode = 'demo'
            self.imgFrame.configure({'name': {'text': data['name']+" (demo)"}})
            # self.is_loaded_survey = True
            # self.__survey_parse(data)
            # self.is_filling_survey = False

    def lock_buttons(self, state: bool):
        if state:
            self.imgFrame.configure({'b1': {'state': DISABLED}, 'b2': {'state': DISABLED},
                                     'b3': {'state': DISABLED}, 'b4': {'state': DISABLED},
                                     'b5': {'state': DISABLED}, 'n1': {'state': DISABLED},
                                     'color': {'state': 'readonly'}})
            self.imgFrame.configure({'n2': {'text': self.imgFrame.language[self.imgFrame.cur_lang]['start'],
                                            'command': lambda: self.__begin_action(), 'state': NORMAL}})
        else:
            # demo or full
            self.imgFrame.configure({'b1': {'state': NORMAL}, 'b2': {'state': NORMAL},
                                     'b3': {'state': NORMAL}, 'b4': {'state': NORMAL},
                                     'b5': {'state': NORMAL}, 'n1': {'state': NORMAL},
                                     'color': {'state': DISABLED}})
            self.imgFrame.configure({'n2': {'text': self.imgFrame.language[self.imgFrame.cur_lang]['n2']}})

    def start(self):
        self.tk.mainloop()

    def __init_experiment(self) -> bool:
        if self.experiment.status != 'init':
            success = self.experiment.init_experiment()
            if not success:
                print('not init experiment')
                CustomDialog.ok_dialog(self.tk, 'noexpertitle', 'noexpermessage')
                # todo
                return False
            return True
        return True


    def __start_experiment(self):

        if self.imgFrame.color.current() == -1:
            CustomDialog.ok_dialog(self.tk,'colormodetitle', 'colormodemessage')
            return
        if not self.__init_experiment():
            return
        # print(f"start experiment ({self.experiment.mode})")
        self.lock_buttons(False)
        # win.destroy()
        # self.experiment.mode == "demo" / "full"
        self.experiment.start_experiment()




class Experiment:
    # todo: шаблон значення, з заміною на актуальні для поточної ситуації
    # todo: прогрес-бар вначале для всех изображений,  в процессе загрузки только для загружаеміх, потом возврат

    def __init__(self, gui: GUI):
        self.gui = gui
        self.status = 'none'
        self.mode = 'none'
        self.round = 0
        self.pairs = []
        self.results = []
        self.returns: int = 0
        self.begin_time: float = 0
        self.end_time: float = 0
        self.times = []

    def get_images_stats(self):
        # todo
        pass

    def init_experiment(self) -> bool:

        if self.mode == 'demo':
            return self.init_demo()

        if self.gui.imgFrame.color.current() == 0:  # color
            tmp = list(filter(os.path.isfile, Path('images').glob('*_color_gt.png')))
            ref_images = dict(zip([re.split('_gt', r.name)[0] for r in tmp], tmp))

            tmp = list(filter(os.path.isfile, Path('images').glob('*_color_recon.png')))
            dist_images = dict(zip([re.split('_recon', d.name)[0] for d in tmp], tmp))
        else:
            tmp = list(filter(os.path.isfile, Path('images').glob('*_gray_gt.png')))
            ref_images = dict(zip([re.split('_gt', r.name)[0] for r in tmp], tmp))

            tmp = list(filter(os.path.isfile, Path('images').glob('*_gray_recon.png')))
            dist_images = dict(zip([re.split('_recon', d.name)[0] for d in tmp], tmp))

        # ref_names = [re.split('_gt', r.name)[0] for r in ref_images]
        # dist_names = [re.split('_recon', d.name)[0]  for d in dist_images]

        # check pairs equality
        if ref_images.keys() == dist_images.keys():
            validity = True
        else:
            validity = False

        # print(f'validation: {validity}')

        # random pairs
        pairs = []
        for r in ref_images.keys():
            pairs.append((ref_images[r].name, dist_images[r].name))
        random.shuffle(pairs)

        self.status = 'init'
        self.pairs = pairs
        self.rounds = len(pairs)
        self.results = [0] * self.rounds
        self.times = [0.0] * self.rounds
        self.round = 0
        return True

    def init_demo(self) -> bool:

        if self.gui.imgFrame.color.current() == 0:
            demo_images = ("2022_SERC_6_369000_4303000_0.98_color",
                           "2022_SERC_6_358000_4301000_0.98_color",
                           "2022_SERC_6_358000_4304000_0.98_color",
                           "2022_SERC_6_362000_4310000_0.98_color",
                           "2022_SERC_6_364000_4308000_0.98_color")
        else:
            demo_images = ("2022_SERC_6_358000_4301000_0.98_gray",
                           "2022_SERC_6_358000_4304000_0.98_gray",
                           "2022_SERC_6_362000_4310000_0.98_gray",
                           "2022_SERC_6_364000_4308000_0.98_gray")

        tmp1 = list(filter(os.path.isfile, Path('images').glob('*gt.png')))
        tmp2 = list(filter(os.path.isfile, Path('images').glob('*recon.png')))

        ref_images = dict()
        dist_images = dict()
        pairs = []
        for i in range(len(tmp1)):
            tmp = re.split('_gt', tmp1[i].name)[0]
            if tmp in demo_images:
                ref_images[tmp] = tmp1[i]
                dist_images[tmp] = tmp2[i]
                pairs.append((tmp1[i].name, tmp2[i].name))

        self.status = 'init'
        self.pairs = pairs
        self.rounds = 5
        self.results = [2, 3, 4, 5, 1]
        self.times = [0.0] * self.rounds
        self.round = 0
        return True

    def start_experiment(self):
        self.status = 'started'
        self.gui.imgFrame.configure({'n1': {'command': lambda: self.__previous_action()}})
        self.gui.imgFrame.configure({'n2': {'command': lambda: self.__next_action()}})
        self.begin_time = time.time()
        self.__set_round(0)
        # todo

    def __set_round(self, r: int):
        self.round = r
        self.__n1_n2_options()
        self.gui.imgFrame.set_selection(self.results[self.round])
        self.gui.imgFrame.configure({'progress': {'value': round(self.round / (self.rounds-1) * 100)}})
        self.gui.imgFrame.set_ref_image(self.pairs[r][0])
        self.gui.imgFrame.set_dist_image(self.pairs[r][1])

    def __next_action(self):
        if self.round >= self.rounds:
            return

        self.results[self.round] = self.gui.imgFrame.get_selection()
        if self.round == self.rounds - 1:
            self.__save_results()
            return
        # print(self.results)
        if self.round < self.rounds - 1:
            if self.returns > 0:
                self.returns -= 1
            if self.returns == 0:
                self.times[self.round] = time.time()
            self.__set_round(self.round + 1)

    def __previous_action(self):
        if self.round < 0:
            return
        self.results[self.round] = self.gui.imgFrame.get_selection()
        print(self.results)
        if self.round > 0:
            self.returns += 1
            self.__set_round(self.round - 1)

    def __n1_n2_options(self):
        if self.round == self.rounds - 1:
            self.gui.imgFrame.configure({'n2': {'text': self.gui.imgFrame.language[self.gui.imgFrame.cur_lang]['save']}})
        else:
            self.gui.imgFrame.configure({'n2': {'text': self.gui.imgFrame.language[self.gui.imgFrame.cur_lang]['n2']}})


    def __save_results(self):

        if self.mode == "demo":
            self.__clear()
            self.mode = "full"
            self.gui.lock_buttons(True)
            return

        self.end_time = time.time()
        self.times[-1] = self.end_time

        saved_result = dict()
        saved_result['name'] = YAML.read(list(filter(os.path.isfile, Path('results').glob('*survey.yaml')))[0])['name']
        saved_result['start_time'] = self.__formatted_time('%Y-%m-%d %H:%M:%S', self.begin_time)
        saved_result['end_time'] = self.__formatted_time('%Y-%m-%d %H:%M:%S', self.end_time)
        saved_result['markers'] = [self.begin_time, self.end_time]
        saved_result['rnd'] = random.randint(1000000, 9999999)
        # saved_result['conf_version'] = self.gui.conf_version
        # saved_result['app_version'] = self.gui.version

        res = []
        for i, p in enumerate(self.pairs):
            res.append([p[0], self.results[i], self.times[i]])
        # print(res)
        saved_result['results'] = res

        file_name = f"{saved_result['name']} {self.__formatted_time('%Y-%m-%d %H.%M.%S', self.begin_time)}.yaml"
        YAML.write(saved_result, file_name, 'results')

        Network.upload_file(saved_result['name'], file_name, 'results')
        # to do yaml
        # to do upload
        self.__clear()
        CustomDialog.ok_dialog(self.gui.tk, 'savetitle', 'savemessage')
        self.gui.lock_buttons(True)
        # self.gui.load_dialog(self.gui.tk)

    @staticmethod
    def __formatted_time(pattern: str, t: float) -> str:
        return time.strftime(pattern, time.localtime(t))

    def __clear(self):
        self.round = 0
        self.pairs = []
        self.results = []
        self.status = 'none'
        self.gui.imgFrame.set_selection(0)
        # self.gui.imgFrame.set_ref_image(None)
        self.returns = 0
        self.begin_time = 0
        self.end_time = 0
        self.times = []




class CustomFrame(ABC):

    def __init__(self, parent: Tk):
        frame = Frame(parent)
        self.tk = parent
        self._layout(frame)

    def _layout(self, frame: Frame) -> None:
        frame.grid()
        # self.font = font.nametofont('TkDefaultFont')
        # self.font['size'] = 11

    @abstractmethod
    def get_frame(self) -> Frame:
        pass

    def configure(self, widgets_config: dict) -> None:
        widgets = widgets_config.keys()
        for widget in widgets:
            getattr(self, widget).config(**widgets_config[widget])


class ImageFrame(CustomFrame):
    impath = 'images'
    colormodels = ['color','gray']
    lang_list = {'en': 'EN', 'ua': 'UA'}
    language = {
        'en': {
            'b1': "Terrible (1)",
            'b2': "Bad (2)",
            'b3': "Average (3)",
            'b4': "Good (4)",
            'b5': "Excellent (5)",
            'n1': "<< Previous",
            'n2': "Next >>",
            'notification': "---",
            'start': "Start",
            'save': "Save",
            'title': "MOS estimation test (v2.0)"},
        'ua':{
            'b1': "Жахливе (1)",
            'b2': "Погане (2)",
            'b3': "Середнє (3)",
            'b4': "Гарне (4)",
            'b5': "Бездоганне (5)",
            'n1': "<< Попереднє",
            'n2': "Наступне >>",
            'notification': "---",
            'start': "Старт",
            'save': "Зберегти",
            'title': "Тест з визначення MOS (v2.0)"}
        }
    cur_lang = 'en'

    def __init__(self, parent: Tk = None) -> None:
        self.dist_img = None
        self.ref_img = None
        self.selection: int = 0
        super().__init__(parent)

    def _layout(self, frame: Frame) -> None:
        self.__frame = frame
        super()._layout(frame)
        self.tk.title(self.language[self.cur_lang]['title'])

        self.ref_canvas = ZoomedCanvas(frame, image=self.ref_img)
        self.ref_canvas.grid(row=1, column=0, padx=10, pady=2)
        self.dist_canvas = ZoomedCanvas(frame, image=self.dist_img)
        self.dist_canvas.grid(row=1, column=1, padx=(0, 10), pady=2)

        self.dist_canvas.bind("<Motion>", self.mouse_motion)
        self.ref_canvas.bind("<Motion>", self.mouse_motion)
        frame.bind("<Motion>", self.mouse_motion)

        # ---
        fr1 = Frame(frame)
        fr1.grid(row=0, column=0, columnspan=2, padx=6, pady=5, sticky=E+W)
        fr1.columnconfigure(1, weight=1)
        self.name = Label(fr1, text="Name", anchor="w", justify="left")
        self.name.grid(row=0, column=0, padx=(5, 10), pady=2, sticky=W)
        self.progress = ttk.Progressbar(fr1, orient="horizontal", length=300, value=0)
        self.progress.grid(row=0, column=2, columnspan=2, padx=5, pady=2, sticky=S + E + W)

        colormod = StringVar()
        self.color = ttk.Combobox(fr1, textvariable=colormod, values=self.colormodels, width=15, state="readonly")
        self.color.grid(row=0, column=4, padx=5, pady=2, sticky=S + E + W)

        # colormod = StringVar()
        self.lang = ttk.Combobox(fr1, values=list(self.lang_list.values()), width=15, state="readonly")
        self.lang.current(0)
        self.lang.grid(row=0, column=1, padx=5, pady=2, sticky=E)

        fr2 = Frame(frame, bd=2, relief=RIDGE)
        fr2.grid(row=2, column=0, columnspan=2, padx=12, pady=5, sticky=E+W)
        fr2.grid_columnconfigure(0, weight=1)
        # fr2.grid_columnconfigure(1, weight=0)
        fr2.grid_columnconfigure(2, weight=1)
        self.b1 = Button(fr2, text=self.language[self.cur_lang]['b1'], width=15, height=2,
                         command=lambda: self.__test_action(1, True), relief=RAISED)
        self.b1.grid(row=0, column=0, padx=5, pady=2, sticky=E)
        self.b2 = Button(fr2, text=self.language[self.cur_lang]['b2'], width=15, height=2,
                         command=lambda: self.__test_action(2, True), relief=RAISED)
        self.b2.grid(row=0, column=1, padx=5, pady=2)
        self.b3 = Button(fr2, text=self.language[self.cur_lang]['b3'], width=15, height=2,
                         command=lambda: self.__test_action(3, True), relief=RAISED)
        self.b3.grid(row=0, column=2, padx=5, pady=2, sticky=W)
        self.b4 = Button(fr2, text=self.language[self.cur_lang]['b4'], width=15, height=2,
                         command=lambda: self.__test_action(4, True), relief=RAISED)
        self.b4.grid(row=0, column=3, padx=5, pady=2, sticky=E)
        self.b5 = Button(fr2, text=self.language[self.cur_lang]['b5'], width=15, height=2,
                         command=lambda: self.__test_action(5, True), relief=RAISED)
        self.b5.grid(row=0, column=4, padx=5, pady=2)

        fr3 = Frame(frame)
        fr3.grid(row=3, column=0, columnspan=2, padx=6, pady=6, sticky=E+W)
        self.notification = Label(fr3, text=self.language[self.cur_lang]['notification'], anchor="w", justify="left")
        self.notification.grid(row=0, column=0, padx=(5, 10), pady=2, sticky=W)
        self.n1 = Button(fr3, text=self.language[self.cur_lang]['n1'], width=15, height=2)
        self.n1.grid(row=0, column=1, padx=5, pady=2, sticky=E)
        self.n2 = Button(fr3, text=self.language[self.cur_lang]['n2'], width=15, height=2)
        self.n2.grid(row=0, column=2, padx=5, pady=2, sticky=E)
        fr3.grid_columnconfigure(1, weight=1)

    def __test_action(self, button_id: int, action: bool = True):

        if button_id == 0:
            self.selection = 0
            for i in range(1, 6):
                button = getattr(self, f'b{i}')
                button['relief'] = RAISED
        else:
            for i in range(1, 6):
                button = getattr(self, f'b{i}')
                if button_id != i:
                    button['relief'] = RAISED
                else:
                    if not action:
                        button['relief'] = SUNKEN
                        self.selection = i
                    elif button['relief'] == RAISED:
                        self.selection = i
                        button['relief'] = SUNKEN
                    else:
                        self.selection = 0
                        button['relief'] = RAISED

        if self.selection == 0:
            self.n1['state'] = DISABLED
            self.n2['state'] = DISABLED
        else:
            self.n1['state'] = NORMAL
            self.n2['state'] = NORMAL

    def set_selection(self, value: int = 0):
        if value not in [0,1,2,3,4,5]:
            value = 0
        self.__test_action(value, False)

    def get_selection(self) -> int:
        return self.selection

    def set_ref_image(self, image_name: str) -> None:
        path = os.path.join(self.impath, image_name)
        self.ref_img = Image.open(path, mode='r')
        self.ref_canvas.set_image(self.ref_img)

    def set_dist_image(self, image_name: str) -> None:
        path = os.path.join(self.impath, image_name)
        self.dist_img = Image.open(path, mode='r')
        self.dist_canvas.set_image(self.dist_img)

    def get_frame(self) -> Frame:
        return self.__frame

    def init_lang_action(self, gui: GUI):
        self.gui_link = gui
        self.lang.bind('<<ComboboxSelected>>', lambda lang=self.lang.get().lower(): self.__select_lang(lang))

    def __select_lang(self, lang: str):
        lang = self.lang.get().lower()
        self.cur_lang = lang
        self.tk.title(self.language[self.cur_lang]['title'])
        self.notification['text'] = self.language[self.cur_lang]['notification']
        self.b1['text'] = self.language[self.cur_lang]['b1']
        self.b2['text'] = self.language[self.cur_lang]['b2']
        self.b3['text'] = self.language[self.cur_lang]['b3']
        self.b4['text'] = self.language[self.cur_lang]['b4']
        self.b5['text'] = self.language[self.cur_lang]['b5']

        self.n1['text'] = self.language[self.cur_lang]['n1']
        self.n2['text'] = self.language[self.cur_lang]['start'] if self.n1['state'] == DISABLED else (
            self.language)[self.cur_lang]['n2']
        self.gui_link.cur_lang = lang

    def mouse_motion(self, event):
        cx = 0
        cy = 0
        if isinstance(event.widget, Canvas):
            cx = event.x - 4
            cy = event.y - 4
            # cx=self.winfo_pointerx() - self.winfo_rootx()
            # cy=self.winfo_pointery() - self.winfo_rooty()
        self.dist_canvas.after(0, self.dist_canvas.canvas_zooming(event, cx, cy))
        self.ref_canvas.after(0, self.ref_canvas.canvas_zooming(event, cx, cy))


class ZoomedCanvas(Canvas):

    def __init__(self, master: Frame = None, image=None) -> None:
        # self.image = image
        # if image is None:
        w, h = (192, 192)
        super().__init__(master, height=h, width=w)
        self.photoimg = None
        self.pilzoom = None
        # else:
        #     self.photoimg = ImageTk.PhotoImage(image)
        #     w, h = image.size
        #     self.pilzoom = image.resize((w*2, h*2), Image.ANTIALIAS)
        #     # self.zoomimg = self.photoimg._PhotoImage__photo.zoom(2)
        #     super().__init__(master, height=h, width=w)
        #     self.create_image(4, 4, image=self.photoimg, anchor=NW)
        self.is_zoomed = False
        self.config(bd=2, relief=RIDGE)

    def set_image(self, image):
        self.photoimg = ImageTk.PhotoImage(image)
        w, h = image.size
        self.pilzoom = image.resize((w * 2, h * 2), Image.LANCZOS)
        self.create_image(4, 4, image=self.photoimg, anchor=N+W)
        self.is_zoomed = False

    def canvas_zooming(self, event, cx, cy):
        if isinstance(event.widget, Canvas) and self.photoimg is not None:
            # cx=self.winfo_pointerx() - self.winfo_rootx()
            # cy=self.winfo_pointery() - self.winfo_rooty()

            area = (cx, cy, cx + self.photoimg.width(), cy + self.photoimg.height())
            self.tmp = ImageTk.PhotoImage(self.pilzoom.crop(area))
            self.create_image(4, 4, image=self.tmp, anchor=N+W)
            # self.create_image(-cx, -cy, image=self.zoomimg, anchor=NW)
            self.is_zoomed = True

        else:
            if self.is_zoomed:
                self.create_image(4, 4, image=self.photoimg, anchor=N+W)
                self.is_zoomed = False


class EntryWithHint(Entry):
    def __init__(self, master=None, hint="", color='grey'):
        super().__init__(master)
        self.hint = hint
        self.hint_color = color
        self.default_fg_color = self['fg']
        self.bind("<FocusIn>", self.foc_in)
        self.bind("<FocusOut>", self.foc_out)

        self.put_hint()

    def put_hint(self):
        self.insert(0, self.hint)
        self['fg'] = self.hint_color

    def foc_in(self, *args):
        if self['fg'] == self.hint_color:
            self.delete('0', 'end')
            self['fg'] = self.default_fg_color

    def foc_out(self, *args):
        if not self.get():
            self.put_hint()


# static classes
class ModalDialog:
    """Unified modal dialog for the app"""

    @staticmethod
    def create_dialog(parent_window: Tk = None, title: str = "Info", modal: bool = True,
                      resizable=(False, False)) -> Toplevel:
        win = Toplevel(parent_window)
        win.grid()
        win.resizable(*resizable)
        win.title(title)

        # parent_window.eval('tk::PlaceWindow . center')
        coords = (parent_window.winfo_x(), parent_window.winfo_y(), parent_window.winfo_width(),
                  parent_window.winfo_height())
        win.geometry(f'+{round(coords[0] + coords[2] / 2)}+{round(coords[1] + coords[3] / 2)}')

        if modal:
            ModalDialog.__dialog_make_modal(win, parent_window)
        return win

    @staticmethod
    def __dialog_make_modal(window, parent_window):
        """
        Make a modal dialog if required
        :param parent_window: parent window
        """
        window.focus_set()  # принять фокус ввода,
        window.grab_set()  # запретить доступ к др. окнам, пока открыт диалог (not Linux)
        # self.win.wait_window() # not for quit
        window.transient(parent_window)  # + Linux(запретить доступ к др. окнам)


class CustomDialog:
    @staticmethod
    def _messages(lang:str) -> dict:
        messages = {
            'en': {
                'exit': "Exit",
                'exit_question': "Exit the program?",
                'yes': "Yes",
                'no': "No",
                'survey': "Survey",
                'survey_mistake': "Incorrect data",
                'load': "Loading",
                'noinetmessage': "No permission to\nconnect to the Internet",
                'noinettitle': "No permission",
                'noexpertitle': "Experiment error",
                'noexpermessage': "Unable to run experiment, insufficient number of images",
                'needloadtitle': "Download required",
                'needloadmessage': "The missing images must be loaded to start the experiment",
                'newveriontitle': "Update the program",
                'newversionmessage': "A new version of the program has been\npublished. Please update using the link:",
                'newversionlink': "https://github.com/OlegIeremeiev/Lidar_MOS_experiment",
                'noimagetitle': "No image",
                'noimagemessage': "No images are found. Program will close",
                'savetitle': "Saving",
                'savemessage': "The result was saved successfully",
                'colormodetitle': "Warning!",
                'colormodemessage': "Color model of the images is not selected"
            },
            'ua': {
                'exit': "Вихід",
                'exit_question': "Вийти з програми?",
                'yes': "Так",
                'no': "Ні",
                'survey': "Опитування",
                'survey_mistake': "Некоректні дані",
                'load': "Завантаження",
                'noinetmessage': "Немає дозволу\nпідключитися до Інтернет",
                'noinettitle': "Немає дозволу",
                'noexpertitle': "Помилка експерименту",
                'noexpermessage': "Неможливо запустити експеримент, недостатня кількість зображень",
                'needloadtitle': "Потрібне завантаження",
                'needloadmessage': "Відсутні зображення мають бути\nзавантажені для старту експерименту",
                'newveriontitle': "Оновлення програми",
                'newversionmessage': "Опубліковано нову версію програми. Будь ласка оновіть за посиланням:",
                'newversionlink': "https://github.com/OlegIeremeiev/Lidar_MOS_experiment",
                'noimagetitle': "Немає зображень",
                'noimagemessage': "Зображення не знайдені. Програма буде закрита",
                'savetitle': "Збереження",
                'savemessage': "Результат був успішно збережений",
                'colormodetitle': "Попередження!",
                'colormodemessage': "Не обрано кольорову модель зображень"
            }
        }
        return messages[lang]

    @staticmethod
    def quit_dialog(parent_window: Tk | Toplevel | None, lang: str = 'en'):
        """
        Create custom dialog window for program quit
        :param parent_window: main frame to which this dialog needs to be attached
        :param language: selected language for all messages
        """
        messages = CustomDialog._messages(lang)
        win = ModalDialog.create_dialog(parent_window, title=messages['exit'])

        Label(win, text=messages['exit_question']) \
            .grid(column=0, row=0, columnspan=2, sticky=N+S, padx=10, pady=2)
        Button(win, text=messages['yes'], command=parent_window.quit, width=5) \
            .grid(column=0, row=1, sticky=NSEW, padx=10, pady=5)
        Button(win, text=messages['no'], command=win.destroy, width=5) \
            .grid(column=1, row=1, sticky=NSEW, padx=10, pady=5)

    @staticmethod
    def survey_dialog(parent_window: Tk | Toplevel | None, lang: str = 'en') -> Toplevel:
        messages = CustomDialog._messages(lang)
        win = ModalDialog.create_dialog(parent_window, title=messages['survey'])
        win.protocol("WM_DELETE_WINDOW", lambda parent=win: CustomDialog.quit_dialog(parent, lang))
        return win

    @staticmethod
    def ok_dialog(parent_window: Tk | Toplevel | None,  title_type, message_type, lang: str = 'en'):
        messages = CustomDialog._messages(lang)
        win = ModalDialog.create_dialog(parent_window, title=messages[title_type])
        Label(win, text=messages[message_type]) \
            .grid(column=0, row=0, sticky=N+S, padx=10, pady=2)
        Button(win, text=messages['yes'], command=win.destroy, width=5) \
            .grid(column=0, row=1, sticky=N+S, padx=10, pady=5)

    @staticmethod
    def noimage_dialog(parent_window: Tk | Toplevel | None,  title_type, message_type, lang: str = 'en'):
        messages = CustomDialog._messages(lang)
        win = ModalDialog.create_dialog(parent_window, title=messages[title_type])
        Label(win, text=messages[message_type]) \
            .grid(column=0, row=0, sticky=N+S, padx=10, pady=2)
        Button(win, text=messages['yes'], command=parent_window.quit, width=5) \
            .grid(column=0, row=1, sticky=N+S, padx=10, pady=5)


class Network:

    # def __init__(self):
    #     self.folder_id = 'kZqDKsZ2AgMjJJTgpBAc2pfWpDzi55iOysX'
    #     self.path = 'images'
    #     self.json = dict()

    @staticmethod
    def upload_file(user_name, file_name: str, path: str) -> dict:
        url = 'https://eapi.pcloud.com/uploadtolink'
        code = 'apQ7ZTjKmwtFEpCQTr3Gv6DYlymuEtUey'

        files = {file_name: open(os.path.join(path, file_name), 'rb')}
        session = requests.Session()
        post = session.post(url, data={'code': code, 'names': user_name}, files=files)
        return post.json()


class SurveyFrame(CustomFrame):
    language = {
        'en': {
            'intro': "Control questions about the conditions for\nconducting experiments on the distortions visibility",
            'name': "Name:",
            'name_hint': "Name, Surname",
            'age': "Age:",
            'device_type': ["Device type:", "Monitor", "Laptop", "Projector", "Other"],
            'device': "Device model:",
            'screen_size': "Screen diagonal (inch):",
            'resolution': "Resolution:",
            'resolution_hint': "1920x1080",
            'luminance': "Screen brightness (%):",
            'light': ["Room lighting:", "artificial", "natural"],
            'description': "The listed factors significantly affect\nthe results of experiments and are mandatory to enter\n(used only for statistical studies)",
            'save': "Save"},
        'ua': {
            'intro': "Контрольні питання про умови проведення експерименту з помітності завад",
            'name': "Ім'я:",
            'name_hint': "Ім'я, Прізвище",
            'age': "Вік:",
            'device_type': ["Тип пристрою:", "Монітор", "Ноутбук", "Проектор", "Інше"],
            'device': "Модель пристрою:",
            'screen_size': "Діагональ екрану (дюйми):",
            'resolution': "Роздільна здатність:",
            'resolution_hint': "1920x1080",
            'luminance': "Яскравість екрану (%):",
            'light': ["Освітлення приміщення:", "штучне", "природнє"],
            'description': "Перераховані фактори суттєво впливають на\nрезультати експерименту і обов'язкові для внесення\n(використовуються лише для статистичних досліджень)",
            'save': "Зберегти"}
    }

    def __init__(self, parent: Tk | Toplevel | None = None, lang: str = 'en') -> None:
        super().__init__(parent)
        self.cur_lang = lang

    def _layout(self, frame: Frame) -> None:
        self.__frame = frame
        super()._layout(frame)
        self.labels = dict()
        Label(frame, text=self.language[self.cur_lang]['intro'], anchor="w", justify="left") \
            .grid(row=0, column=0, columnspan=2, sticky=E+W, padx=5, pady=2)

        self.labels['name'] = Label(frame, text=self.language[self.cur_lang]['name'], anchor="w", justify="left")
        self.labels['name'].grid(row=1, column=0, sticky=E+W, padx=5, pady=2)
        self.name = EntryWithHint(frame, hint=self.language[self.cur_lang]['name_hint'])
        self.name.config(width=30)
        self.name.grid(row=1, column=1, sticky=E+W, padx=5, pady=2)

        self.labels['age'] = Label(frame, text=self.language[self.cur_lang]['age'], anchor="w", justify="left")
        self.labels['age'].grid(row=2, column=0, sticky=E+W, padx=5, pady=2)
        self.age = Scale(frame, variable=IntVar(value=0), from_=0, to=100, orient=HORIZONTAL)
        # self.age = Spinbox(frame, from_=10, to=100, width=10, textvariable=StringVar(value=str(10)))
        self.age.grid(row=2, column=1, sticky=E+W, padx=5, pady=2)

        self.labels['device_type'] = Label(frame, text=self.language[self.cur_lang]['device_type'][0], anchor="w",
                                           justify="left")
        self.labels['device_type'].grid(row=3, column=0, sticky=E+W, padx=5, pady=2)
        def_device = StringVar(value=self.language[self.cur_lang]['device_type'][1])
        self.device_type = ttk.Combobox(frame, textvariable=def_device,
                                        values=self.language[self.cur_lang]['device_type'][1:], width=15,
                                        state="readonly")
        # lst = Listbox(frame, listvariable=Variable(value=), width=15)
        self.device_type.grid(row=3, column=1, sticky=E+W, padx=5, pady=2)

        self.labels['device'] = Label(frame, text=self.language[self.cur_lang]['device'], anchor="w", justify="left")
        self.labels['device'].grid(row=4, column=0, sticky=E+W, padx=5, pady=2)
        self.device = Entry(frame, width=20)
        self.device.grid(row=4, column=1, sticky=E+W, padx=5, pady=2)

        self.labels['screen_size'] = Label(frame, text=self.language[self.cur_lang]['screen_size'], anchor="w",
                                           justify="left")
        self.labels['screen_size'].grid(row=5, column=0, sticky=E+W, padx=5, pady=2)
        self.screen = Entry(frame, width=15)
        self.screen.grid(row=5, column=1, sticky=E+W, padx=5, pady=2)

        self.labels['resolution'] = Label(frame, text=self.language[self.cur_lang]['resolution'], anchor="w",
                                          justify="left")
        self.labels['resolution'].grid(row=6, column=0, sticky=E+W, padx=5, pady=2)
        self.resol = EntryWithHint(frame, hint=self.language[self.cur_lang]['resolution_hint'])  # split by x_ua, x_en
        self.resol.config(width=15)
        self.resol.grid(row=6, column=1, sticky=E+W, padx=5, pady=2)

        self.labels['luminance'] = Label(frame, text=self.language[self.cur_lang]['luminance'], anchor="w",
                                         justify="left")
        self.labels['luminance'].grid(row=7, column=0, sticky=E+W, padx=5, pady=2)
        self.lum = Scale(frame, variable=IntVar(value=-1), from_=-1, to=100, orient=HORIZONTAL)
        # self.lum = Spinbox(frame, from_=-1, to=100, width=10, textvariable=StringVar(value=str(-1)))
        self.lum.grid(row=7, column=1, sticky=E+W, padx=5, pady=2)

        self.labels['light'] = Label(frame, text=self.language[self.cur_lang]['light'][0], anchor="w", justify="left")
        self.labels['light'].grid(row=8, column=0, sticky=E+W, padx=5, pady=2)
        self.light = ttk.Combobox(frame, values=self.language[self.cur_lang]['light'][1:], width=15, state="readonly")
        self.light.grid(row=8, column=1, sticky=E+W, padx=5, pady=2)

        Label(frame, text=self.language[self.cur_lang]['description'], anchor="w", justify="left") \
            .grid(row=9, column=0, columnspan=2, sticky=E+W, padx=5, pady=2)
        self.button = Button(frame, text=self.language[self.cur_lang]['save'])
        self.button.grid(row=10, column=0, columnspan=2, padx=5, pady=(2, 5))

    def get_data(self) -> dict:

        if self.__data_check():
            data = {
                'name': self.name.get(),
                'age': int(self.age.get()),
                'device_type': self.device_type.current(),
                'device': self.device.get(),
                'screen_size': float(self.screen.get()),
                'resolution': re.split('[xXхХ]', self.resol.get()),
                'luminance': int(self.lum.get()),
                'light': self.light.current(),
                'mark': time.time(),
                'os': [platform.system(), platform.release(), platform.version()]
            }
        else:
            data = dict()
        return data

    def __data_check(self) -> bool:
        is_success = True

        if not self.name.get() or self.name['fg'] == 'grey':
            self.labels['name'].config(fg='red')
            is_success = False
        else:
            self.labels['name'].config(fg='black')

        if int(self.age.get()) == 0:
            self.labels['age'].config(fg='red')
            is_success = False
        else:
            self.labels['age'].config(fg='black')

        if not self.device_type.get():
            self.labels['device_type'].config(fg='red')
            is_success = False
        else:
            self.labels['device_type'].config(fg='black')

        if not self.device.get():
            self.labels['device'].config(fg='red')
            is_success = False
        else:
            self.labels['device'].config(fg='black')

        if not self.screen.get() or not self.screen.get().replace(".", "").replace(",", "").isnumeric():
            self.labels['screen_size'].config(fg='red')
            is_success = False
        else:
            self.labels['screen_size'].config(fg='black')

        if not self.resol.get() or len(re.split('[xXхХ]', self.resol.get())) < 2 or \
                self.resol['fg'] == 'grey':
            self.labels['resolution'].config(fg='red')
            is_success = False
        else:
            self.labels['resolution'].config(fg='black')

        if int(self.lum.get()) == -1:
            self.labels['luminance'].config(fg='red')
            is_success = False
        else:
            self.labels['luminance'].config(fg='black')

        if not self.light.get():
            self.labels['light'].config(fg='red')
            is_success = False
        else:
            self.labels['light'].config(fg='black')

        return is_success

    def get_frame(self) -> Frame:
        return self.__frame


class YAML:
    @staticmethod
    def read(name: str, path: str = "") -> dict:
        with open(os.path.join(path, name), 'r') as file:
            data = yaml.safe_load(file)
        return data

    @staticmethod
    def write(data: dict, name: str, path: str = ""):
        with open(os.path.join(path, name), "w") as file:
            yaml.dump(data, file, allow_unicode=True)



if __name__ == "__main__":
    GUI().start()
