import ast
import sys
import time
from collections import namedtuple
import tkinter as tk
from tkinter.ttk import Style
from PIL import Image, ImageTk, ImageOps
from PIL.ImageTk import PhotoImage
from numpy import ndarray
import numpy as np
import cv2
import tifffile as tf
import pytesseract
from sys import platform
from enum import Enum
from tkinter import Frame, StringVar, Button, Label, Listbox, Event, \
    Scrollbar, BOTTOM, END, RIGHT, HORIZONTAL, VERTICAL, BOTH, LEFT, X, Y, W, ttk, Toplevel, Canvas, \
    messagebox, BooleanVar, DoubleVar, Text
import traceback
import os
import glob
from typing import List, TypedDict, Tuple, Union, Self, Any
import re
import yaml

from database.sqlite3db import DB

YAML_FILE = 'FPARSTruth'
with open(f'truther' + os.sep + f'{YAML_FILE}.yml', 'r') as f:
    yml_data = yaml.safe_load(f)
is_wsl = False
if platform.startswith("linux"):
    for c in yml_data['LINUX']['TESSDATA_PREFIX']:
        if os.path.exists(c):
            os.environ['TESSDATA_PREFIX'] = c
            break
    for c in yml_data['LINUX']['TESSERACT_CMD']:
        if os.path.exists(c):
            pytesseract.pytesseract.tesseract_cmd = c
            is_wsl  = True
            break
if not is_wsl and platform.startswith("linux"):
    TOP_CANVAS_X, TOP_CANVAS_Y = yml_data['LINUX']['TOP_CANVAS_X'], yml_data['LINUX']['TOP_CANVAS_Y']
    TOP_ROI_CANVAS_COORDS = yml_data['LINUX']['TOP_ROI_CANVAS_COORDS']
    MASTER_GEOMETRY = yml_data['LINUX']['MASTER_GEOMETRY']
    FONT = yml_data['LINUX']['FONT']
    UNRESOLVABLE_BUTTON_ON = yml_data['LINUX']['UNRESOLVABLE_BUTTON_ON']
else:
    if not is_wsl:
        pytesseract.pytesseract.tesseract_cmd = yml_data['WINDOWS']['TESSERACT_CMD']
    TOP_CANVAS_X, TOP_CANVAS_Y = yml_data['WINDOWS']['TOP_CANVAS_X'], yml_data['WINDOWS']['TOP_CANVAS_Y']
    TOP_ROI_CANVAS_COORDS = yml_data['WINDOWS']['TOP_ROI_CANVAS_COORDS']
    MASTER_GEOMETRY = yml_data['WINDOWS']['MASTER_GEOMETRY']
    FONT = yml_data['WINDOWS']['FONT']
    UNRESOLVABLE_BUTTON_ON = yml_data['WINDOWS']['UNRESOLVABLE_BUTTON_ON']

BGR_BLACK = yml_data['BGR_BLACK']
BGR_BLUE = yml_data['BGR_BLUE']

CANVAS_SIDE_X, CANVAS_SIDE_Y = yml_data['CANVAS_SIDE']['X'], yml_data['CANVAS_SIDE']['Y']
PAD_X = yml_data['PAD_X']
EXTENSIONS = yml_data['EXTENSIONS']
ROI_SCALES = yml_data['ROI_SCALES']
SCALE = yml_data['SCALE']
TESSERACT_SINGLE_LINE = yml_data['TESSERACT_SINGLE_LINE']
TESSERACT_MULTI_LINE = yml_data['TESSERACT_MULTI_LINE']
ROTATIONS = yml_data['ROTATIONS']
TEXT_AREA_FONT = yml_data['TEXT_AREA_FONT']
EXTRA_SCROLL = yml_data['EXTRA_SCROLL']
TRUTHER = 'TRUTHER'
REVIEWER = 'REVIEWER'
TOP_CANVAS_COORDS = '+' + str(TOP_CANVAS_X) + '+' + str(TOP_CANVAS_Y)
MODES = Enum('MODES',[TRUTHER, REVIEWER])

IMAGE_NAME, IMAGE_ID, FIELDS, TIME, LINE_NUMBER, TEXT, ADD_BLOCK_ROI, ADD_LINE_ROI, ANGLE = \
    'IMAGE_NAME', 'IMAGE_ID', 'FIELD', 'TIME', 'LINE_NUMBER', 'TXT', 'ADD_BLOCK_ROI', 'ADD_LINE_ROI', 'ANGLE'
Fields = namedtuple('Fields', [LINE_NUMBER, TEXT, ADD_BLOCK_ROI, ADD_LINE_ROI, ANGLE])

class Truth:
    def __init__(self, image_id: str, image_name: str):
        self.image_id = image_id
        self.image_name = image_name
        self.fields = dict()
    #################################################
class Rect:
    @classmethod
    def new_instance(cls, roi: Union[Self, List, Tuple, str]):
        if isinstance(roi, list):
            pass
        elif isinstance(roi, Rect):
            return cls(roi.x, roi.y, roi.w, roi.h)
        elif isinstance(roi, str):
            if roi.strip() != "":
                roi = ast.literal_eval(roi)
            else:
                return cls(0, 0, 0, 0)
        elif isinstance(roi, tuple):
            return cls(roi[0], roi[1], abs(roi[2] - roi[0]), abs(roi[3] - roi[1]))
        else:
            print("ERROR: Invalid arguments to Rectangle constructor(new_instance)")
            return
        return cls(roi[0][0], roi[0][1], abs(roi[1][0] - roi[0][0]), abs(roi[1][1] - roi[0][1]))

    def __init__(self, x: int, y: int, w: int, h: int):
        self.x, self.y = x, y
        self.w, self.h = w, h

    def top_left(self) -> Tuple[int, int]:
        return self.x, self.y

    def bot_right(self) -> Tuple[int, int]:
        return self.x + self.w, self.y + self.h

    def bottom(self) -> int:
        return self.y + self.h

    def right(self) -> int:
        return self.x + self.w

    def area(self) -> int:
        return self.w * self.h

    def union(self, b: Self) -> Self:
        posX = min(self.x, b.x)
        posY = min(self.y, b.y)
        return Rect(posX, posY, max(self.right(), b.right()) - posX, max(self.bottom(), b.bottom()) - posY)

    def region(self) -> Tuple[int, int, int, int]:
        return self.x, self.y, self.x + self.w, self.y + self.h

    def scale(self, scale: float) -> Self:
        return Rect(round(scale * self.x), round(scale * self.y), round(scale * self.w), round(scale * self.h))

    def to_str(self) -> str:
        return str([[self.x, self.y], [self.x + self.w, self.y + self.h]])


################################################################333
def perform_osd(img: ndarray) -> float:
    try:
        osd = pytesseract.image_to_osd(img)
        e = re.search('(?<=Rotate: )[0-9]+', osd).group(0)
        return - float(e)
    except:
        return 0.0

def getMaskedBox(img: ndarray, white: bool = False, threshold: int = 255) -> Tuple[Image, Image]:
    if white:
        _, mask = cv2.threshold(img, 180, 255, cv2.THRESH_BINARY_INV)
        img = cv2.bitwise_not(img)
        mask = Image.fromarray(mask).convert('L')
    else:
        _, mask = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY_INV)
        mask = Image.fromarray(mask).convert('L')

    rgb_pil = Image.fromarray(img).convert('RGB')
    return mask, rgb_pil


class FPARSTruthClass:
    @classmethod
    def truther(cls, master: tk.Tk, db_file: str, is_reviewer: bool = False):
        cls(master, db_file, is_reviewer)

    def __init__(self, master: tk.Tk, db_file: str = None, is_reviewer: bool = False):
        self.canvas_frame = None
        self.resized_img = None
        self.x_view = self.y_view = 0.0
        self.coords = self.coords_roi = self.click_coords = None
        self.cropped_roi = self.unchopped_roi = self.roi = self.canvasROI = self.aRect = self.aRect_roi = None
        self.index = None
        self.field_idx_selected = None
        self.truth_dict = None
        self.times = None
        self.img_scale = None
        self.extension = self.ocr = self.image_id = None
        self.in_path = None
        self.rois = self.inner_rois = None
        self.pasted_photo = None
        self.pasted_size = None
        self.field_tuple = None
        self.cropped_img_inner = self.cropped_img = self.img = None
        self.imageName = None
        self.canvas = None
        self.hbar = self.vbar = None
        self.h = self.w = self.y = self.x = None
        self.truths = dict()

        if db_file is not None:
            self.db_file = db_file
            self.path = None
        else:
            print("ERROR: Invalid arguments provided")
            quit()
        if is_reviewer:
            self.mode = MODES.REVIEWER
        else:
            self.mode = MODES.TRUTHER
        master.geometry(MASTER_GEOMETRY)
        master.title("FPARS Truthing")
        if self.mode == MODES.TRUTHER or self.mode == MODES.REVIEWER:
            self.db = DB(db_file)
        self.rotated_mat = None
        self.current_angle = 0.0
        self.imagesAndIds = {}
        self.paths = None
        self.image_path = None
        self.window = self.windowROI = None
        self.control_frame = Frame(master)
        self.data_frame = Frame(master)
        self.truth_data_frame = Frame(master)
        self.truth_data_box = Listbox(self.truth_data_frame)
        self.control_style = Style(self.control_frame)
        #        self.control_style.configure("TButton", font=FONT)
        self.control_style.configure("TRadiobutton", font=FONT)

        self.control_style.configure("TCheckbutton", font=FONT)

        if platform.startswith("linux"):
            self.lb = Text(self.truth_data_frame, width=350, height=75, font=TEXT_AREA_FONT)
        else:
            self.lb = Text(self.truth_data_frame, width=80, height=20, font=TEXT_AREA_FONT)

        self.vsb = Scrollbar(self.truth_data_box, command=self.lb.yview)
        self.vsb.pack(side="right", fill="y")
        self.lb.configure(yscrollcommand=self.vsb.set)
        self.lb.pack(side="left", fill="both", expand=True)
        self.selection = None

        self.idListFrame = Frame(self.control_frame)
        self.idListBox = Listbox(self.idListFrame)
        self.idListScroll = Scrollbar(self.idListFrame)
        self.idListBox_button_frame = Frame(self.control_frame)
        self.nextButton = Button(self.idListBox_button_frame, text="Next", command=lambda: self.next_selection(1))
        self.prevButton = Button(self.idListBox_button_frame, text="Prev", command=lambda: self.next_selection(-1))
        self.listLabel = Label(self.idListFrame, text="INDEX=null",font=FONT)

        self.idListBox.config(yscrollcommand=self.idListScroll.set)
        self.idListScroll.config(command=self.idListBox.yview)
        self.idListScroll.pack(side=RIGHT, fill=Y)
        self.listLabel.pack(side=BOTTOM)
        self.listLabel.pack(side=BOTTOM)

        self.idListBox.pack()
        self.prevButton.grid(row=0,column=0, sticky=W, padx=PAD_X)
        self.nextButton.grid(row=0,column=1, sticky=W, padx=PAD_X)

        self.idListBox.bind("<<ListboxSelect>>", lambda event: self.list_selected(0))
        self.idListBox.configure(exportselection=False)
        self.idListFrame.grid(row=0, column=0, sticky=W, padx=PAD_X, rowspan=5)
        self.idListBox_button_frame.grid(row=6, column=0, sticky=W, padx=PAD_X)
        self.idsAndImages = self.get_all_ids()

        for id_tag, imageName in self.idsAndImages:
            self.idListBox.insert(END, imageName)
            self.imagesAndIds[imageName] = id_tag

        self.label_image_name = Label(self.control_frame, text="IMAGE ID")
        self.save_button = Button(self.control_frame, text="Save Truth", width=10, height=1,
                                  command=lambda: self.save_data(self.truth_dict))
        self.save_field_button = Button(self.data_frame, text="Save Field", width=10, height=1,
                                        command=lambda: self.save_field_data(self.truth_dict))
        self.ocr_type = StringVar(None, TESSERACT_MULTI_LINE)
        self.single_line_button = ttk.Radiobutton(self.control_frame, text="Single Line", width=10,
                                                  variable=self.ocr_type, value=TESSERACT_SINGLE_LINE,
                                                  command=lambda: self.roi_inner_selected(conf=TESSERACT_SINGLE_LINE))
        self.multi_line_button = ttk.Radiobutton(self.control_frame, text="Multi Line", width=10,
                                                 variable=self.ocr_type, value=TESSERACT_MULTI_LINE,
                                                 command=lambda: self.roi_inner_selected(conf=TESSERACT_MULTI_LINE))
        self.save_button.grid(row=3, column=1, sticky=W, padx=PAD_X)
        self.save_button.grid(row=3, column=1, sticky=W, padx=PAD_X)
        self.save_button.config(font=FONT)
        self.unresolvable_var = BooleanVar(None, False)

        if UNRESOLVABLE_BUTTON_ON:
            self.unresolvable_button = ttk.Checkbutton(self.control_frame, text="Unresolved", width=10,
                                                       variable=self.unresolvable_var,
                                                       command=lambda: self.save_data(self.truth_dict))
            self.unresolvable_button.grid(row=3, column=4, sticky=W, padx=PAD_X)
        self.single_line_button.grid(row=3, column=2, sticky=W, padx=PAD_X)
        self.multi_line_button.grid(row=3, column=3, sticky=W, padx=PAD_X)

        self.control_frame.grid(row=0, column=0, sticky=W, padx=PAD_X)
        self.data_frame.grid(row=1, column=0, sticky=W, padx=PAD_X)
        self.truth_data_frame.grid(row=2, column=0, sticky=W, padx=PAD_X)
        self.scale_var = DoubleVar(None, 1.2)

        r, c, c_start, num_rows = -1, -1, 4, 2
        for scale in ROI_SCALES:
            r += 1
            c += 1
            scale_button = ttk.Radiobutton(self.control_frame, text="ROI scale = " + str(scale), value=scale,
                                           variable=self.scale_var, command=lambda: self.rescale())
            scale_button.grid(row=r % num_rows + 1, column=c_start + c // num_rows, sticky=W, padx=PAD_X)
        r, c, c_start, num_rows = -1, -1, 1, 2
        for rotation in ROTATIONS:
            r += 1
            c += 1
            rotation_button = Button(self.control_frame, text=str(rotation), width=10,
                                     command=lambda x=rotation: self.rotateROI(x))
            rotation_button.config(font=FONT)
            rotation_button.grid(row=r % num_rows + 1, column=c_start + c // num_rows, sticky=W, padx=PAD_X)

    ######################################################
    def clear(self):
        if self.mode == MODES.TRUTHER or self.mode == MODES.REVIEWER:
            self.cropped_roi = None
            self.current_angle = 0.0
            self.rotated_mat = None
            self.roi = None
            self.inner_rois = []
            self.coords = None
            self.lb.delete(0.0, END)
            self.destroy_window(self.windowROI)
            self.windowROI = None
            self.cropped_img = None
            self.img = None
            self.unresolvable_var.set(False)
        self.field_idx_selected = None

    ######################################################
    def next_selection(self,increment: int =1):
        self.list_selected(increment)

    ######################################################
    def rescale(self):
        self.clear()
        self.load_image(is_new_image=True)

    ######################################################
    def list_selected(self, increment: int = 0):
        self.selection = self.idListBox.curselection()
        self.clear()
        self.coords = self.coords_roi = None
        if self.selection and self.selection[0] + increment >= 0 and self.selection[0] + increment < self.idListBox.size():
            self.index = self.selection[0] + increment
            self.selection = (self.index,)
            self.idListBox.selection_clear(0, END)
            self.idListBox.select_set(self.index)
            self.canvas = None
            self.imageName = self.idListBox.get(self.index)
            self.iterate_images(useSameImage=False, useSelectionIdx=True)
            self.image_id = self.imagesAndIds[self.imageName]
            label_txt = str(self.count_done()) + " of " + str(self.count()) +"\n"
            txt = label_txt + "ID = " + str(self.image_id)
            self.listLabel.config(text=txt)

    ######################################################
    def get_all_ids(self) -> Tuple:
        if self.mode == MODES.TRUTHER:
            sql = r'SELECT id,image_name FROM TRUTHS WHERE istruthed = 0 ORDER BY id'
        elif self.mode == MODES.REVIEWER:
            sql = r'SELECT id,image_name FROM TRUTHS WHERE istruthed = 1 ORDER BY id'
        else:
            return ()
        try:
            return self.db.select(sql)
        except Exception:
            print("SELECT id,image_name FAILED: ")
            traceback.print_exc()
            return ()

    ######################################################
    def count_done(self):
        try:
            if self.mode == MODES.REVIEWER:
                sql = r'SELECT COUNT(*) FROM TRUTHS WHERE istruthed = 1'
            else:
                sql = r'SELECT COUNT(*) FROM TRUTHS WHERE istruthed <> 0'
            return self.db.select(sql)[0][0]
        except Exception:
            print("SELECT id,image_name FAILED: ")
            traceback.print_exc()
            return "0"

    ######################################################
    def count(self):
        try:
            sql = r'SELECT COUNT(*) FROM TRUTHS'
            return self.db.select(sql)[0][0]
        except Exception:
            print("SELECT id,image_name FAILED: ")
            traceback.print_exc()
            return "0"

    ######################################################
    def get_all_image_ids(self) -> List[str]:
        return [os.path.splitext(os.path.basename(f))[0] for f in glob.glob(self.path + os.sep + "*")]

    #######################################################
    def click(self, event: Event):
        self.click_coords = self.get_event_point(self.canvas, event)

    #######################################################
    @staticmethod
    def paste_image(pil_over: Image, mask: Image) -> tuple[PhotoImage, Any]:
        pil_img = Image.new('RGBA', mask.size, (255, 255, 255))
        try:
            pil_img.paste(pil_over, (0, 0), mask)
            #pil_img = pil_img.point(lambda x: 0 if x < 100 else 255)
        except Exception:
            traceback.print_exc()
        return ImageTk.PhotoImage(image=pil_img), pil_over.size

    #######################################################
    def drag(self, event: Event):
        x, y = self.get_event_point(self.canvas, event)
        if not self.aRect is None:
            self.canvas.delete(self.aRect)
        self.aRect = self.canvas.create_rectangle(self.click_coords[0], self.click_coords[1], x, y)

    #####################################################
    def release(self, event: Event):
        x, y = max(0, round(self.canvas.canvasx(event.x))), max(0, round(self.canvas.canvasy(event.y)))
        self.current_angle = 0.0
        minX = min(self.click_coords[0], x)
        minY = min(self.click_coords[1], y)
        maxX = max(self.click_coords[0], x)
        maxY = max(self.click_coords[1], y)
        self.coords = Rect(minX, minY, maxX - minX, maxY - minY)
        try:
            self.roi_selected()
        except:
            pass

    #######################################################
    @staticmethod
    def get_event_point(canvas: Canvas, event: Event) -> Tuple[int, int]:
        return round(canvas.canvasx(event.x)), round(canvas.canvasy(event.y))

    #######################################################
    def showROIs(self):
        if not self.windowROI is None:
            self.destroy_window(self.windowROI)
        self.rotated_mat, _, mask, _ = self.rotate_image(self.cropped_img, self.current_angle)
        rgb_pil = Image.fromarray(self.rotated_mat).convert('RGBA')
        self.pasted_photo, self.pasted_size = self.paste_image(rgb_pil, mask)
        self.showROIImg()

    ######################################################
    def showROIImg(self):
        self.windowROI = Toplevel()
        width, height = self.pasted_size
        geometry = str(width) + "x" + str(height)
        self.windowROI.geometry(geometry)
        self.windowROI.geometry(TOP_ROI_CANVAS_COORDS)
        self.canvasROI = Canvas(self.windowROI, width=width, height=height)
        self.canvasROI.create_image(0, 0, state="normal", image=self.pasted_photo, anchor="nw")
        self.canvasROI.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvasROI.bind("<Button-1>", self.clickROI)
        self.canvasROI.bind("<ButtonRelease>", self.releaseROI)
        self.canvasROI.bind("<B1-Motion>", self.dragROI)
    #######################################################
    @staticmethod
    def destroy_window(window: Frame):
        if not window is None:
            window.destroy()

    #######################################################
    def clickROI(self, event: Event):
        self.coords_roi = self.get_event_point(self.canvasROI, event)

    ######################################################
    def dragROI(self, event: Event):
        x, y = self.get_event_point(self.canvasROI, event)
        if not self.aRect_roi is None:
            self.canvasROI.delete(self.aRect_roi)
        self.aRect_roi = self.canvasROI.create_rectangle(self.coords_roi[0], self.coords_roi[1], x, y)

    ######################################################
    @staticmethod
    def get_min_max_of_points(first_click_point: Tuple[int], second_click_point: Tuple[int, int]) -> Tuple[
        int, int, int, int]:
        minX = max(min(first_click_point[0], second_click_point[0]), 0)
        minY = max(min(first_click_point[1], second_click_point[1]), 0)
        maxX = max(first_click_point[0], second_click_point[0])
        maxY = max(first_click_point[1], second_click_point[1])
        return minX, minY, maxX, maxY

    ######################################################
    def releaseROI(self, event: Event):
        self.coords_roi = Rect.new_instance(
            self.get_min_max_of_points(self.coords_roi, self.get_event_point(self.canvasROI, event)))
        self.roi_inner_selected()

    #######################################################
    def load_image(self, is_new_image: bool = True):
        if not self.canvas is None:
            self.x_view = self.canvas.xview()[0]
            self.y_view = self.canvas.yview()[0]
        self.img = None
        self.destroy_window(self.window)
        if is_new_image:
            if not self.in_path is None:
                self.img = tf.imread(self.in_path)
                if self.mode == MODES.TRUTHER or self.mode == MODES.REVIEWER:
                    self.truth_dict = self.populate_truth_dictionary(self.imageName)
        self.populate_ui(self.truth_dict, is_new=is_new_image)
        self.times, self.roi, self.inner_rois = self.get_rois_from_truth_dict(self.truth_dict)

        self.img_scale = cv2.resize(self.img, (0, 0), fx=SCALE, fy=SCALE)

        if not self.inner_rois is None and len(self.inner_rois) > 0:
            self.highlight_rectangle(self.img_scale, self.inner_rois[0], BGR_BLUE, thickness=2)

        if not self.roi is None:
            try:
                scale = self.scale_var.get()
                utx, uty, ubx, uby = self.roi.region()
                self.cropped_img = cv2.resize(self.img[uty:uby, utx:ubx], (0, 0), fx=scale, fy=scale)
                self.rotated_mat, rotated_pil, mask, _ = self.rotate_image(self.cropped_img, self.current_angle)
                mask, rotated_pil = getMaskedBox(self.rotated_mat)

                self.pasted_photo, self.pasted_size = self.paste_image(rotated_pil, mask)
   #            self.pasted_photo(rotated_pil)
                self.showROIImg()
            except:
                print("Image Load Failure: ROI " + self.in_path)
                traceback.print_exc()
        print(self.img_scale.shape)
 #       b, g, r = cv2.split(self.img_scale)
 #       img2 = cv2.merge((r, g, b))
        im = Image.fromarray(self.img_scale)
        self.resized_img = ImageTk.PhotoImage(image=im)
        self.window = Toplevel()
        X_SIDE = CANVAS_SIDE_X
        Y_SIDE = CANVAS_SIDE_Y
        geometry = str(str(X_SIDE) + "x" + str(Y_SIDE))
        self.window.geometry(geometry)
        self.window.geometry(geometry)
        self.window.geometry(TOP_CANVAS_COORDS)
        self.canvas_frame = Frame(self.window, width=X_SIDE, height=Y_SIDE)
        self.canvas_frame.pack(expand=True, fill=BOTH)
        self.canvas_frame.pack(expand=True, fill=BOTH)
        self.canvas = Canvas(self.canvas_frame, bg='#FFFFFF', width=X_SIDE, height=Y_SIDE,
                             scrollregion=(
                             0, 0, self.img_scale.shape[1] + EXTRA_SCROLL, self.img_scale.shape[0] + EXTRA_SCROLL))
        self.hbar = ttk.Scrollbar(self.canvas_frame, orient=HORIZONTAL, style="Canvas.Horizontal.TScrollbar")
        self.hbar.pack(side=BOTTOM, fill=X)
        self.hbar.config(command=self.canvas.xview)
        self.vbar = ttk.Scrollbar(self.canvas_frame, orient=VERTICAL, style="Canvas.Vertical.TScrollbar")
        self.vbar.pack(side=RIGHT, fill=Y)
        self.vbar.config(command=self.canvas.yview)
        #    self.canvas.config(width=self.img_scale.shape[0], height=self.img_scale.shape[1])
        self.canvas.config(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.canvas.pack(side=LEFT, expand=True, fill=BOTH)

        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<ButtonRelease>", self.release)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.canvas.create_image(0, 0, state="normal", image=self.resized_img, anchor="nw")
        self.canvas.xview_moveto(self.x_view)
        self.canvas.yview_moveto(self.y_view)
        if not self.windowROI is None and not self.window is None:
            self.windowROI.lift(aboveThis=self.window)
    #######################################################
    @staticmethod
    def rotate_image(mat: ndarray, angle: float) -> tuple[
        ndarray | Any, Any, Any, tuple[float | Any, float | Any]]:
        # Rotates an image (angle in degrees) and expands image to avoid cropping
        if angle == 0.0:
            mask, rotated_pil = getMaskedBox(mat)
            return mat, rotated_pil,mask,0.0
        height, width = mat.shape[:2]
        image_center = (width / 2, height / 2)
        rotation_mat = cv2.getRotationMatrix2D(image_center, angle, 1.)
        abs_cos = abs(rotation_mat[0, 0])
        abs_sin = abs(rotation_mat[0, 1])
        bound_w = int(height * abs_sin + width * abs_cos)
        bound_h = int(height * abs_cos + width * abs_sin)
        rotation_mat[0, 2] += bound_w / 2 - image_center[0]
        rotation_mat[1, 2] += bound_h / 2 - image_center[1]
        rotated_image = cv2.warpAffine(mat, rotation_mat, (bound_w, bound_h))
        mask, rotated_pil = getMaskedBox(rotated_image)
        '''
        new_width,new_height = rotated_pil.size
        mx = max(new_width,new_height)
        x = round(abs(mx - new_width) // 2)
        y = round(abs(mx - new_height) // 2)
        x_orig = (mx - width) // 2
        y_orig = (mx - height) // 2
        dis_x = round(abs(new_width - width) / 2)
        dis_y = round(abs(new_height - height) / 2)
        '''
        return rotated_image, rotated_pil, mask, image_center

#######################################################
    def iterate_images(self, useSameImage: bool = False, useSelectionIdx: bool = False):
        if useSelectionIdx is True:
            self.idListBox.select_set(self.selection)
        if (self.mode == MODES.TRUTHER or self.mode == MODES.REVIEWER) and self.paths is None:
            self.paths = self.paths = self.db.select("SELECT image_dir FROM PATH ORDER BY time DESC")
        if self.path is not None:
            if self.extension is not None:
                self.in_path = os.path.join(self.path, self.imageName) + '.' + self.extension
            else:
                self.in_path = None
            if self.in_path is None or os.path.exists(self.in_path):
                for ext in EXTENSIONS:
                    self.in_path = os.path.join(self.path, self.imageName) + '.' + ext
                    if os.path.exists(self.in_path):
                        break
                    self.in_path = None
        else:
            for path in self.paths:
                path = str(path[0])
                for ext in EXTENSIONS:
                    self.in_path = os.path.join(path, self.imageName) + '.' + ext
                    if os.path.exists(self.in_path):
                        self.path = path
                        self.extension = ext
                        break

        if self.mode == MODES.REVIEWER or self.mode == MODES.TRUTHER:
            try:
                self.load_image()
            except Exception:
                print("Image Load Failure" + self.in_path)
               # traceback.print_exc()
            return

        if self.idsAndImages is None:
            self.idsAndImages = self.get_all_ids()
        if self.index >= len(self.idsAndImages):
            sys.exit("Your Set is Finished")
        if not useSameImage:
            self.selection = self.idListBox.curselection()
            if self.selection is not None:
                self.imageName = self.idListBox.get(self.index)
                self.image_id = self.imagesAndIds[self.imageName]
        self.rois = []
        self.image_path = ""

        try:
            self.load_image()
        except Exception:
            print("Image Load Failure" + self.in_path)
            traceback.print_exc()

    #######################################################
    def highlight_rectangle(self, img: ndarray, roi: Rect, color: tuple = BGR_BLACK, thickness: int = 2):
        if roi is not None:
            roi = self.scaleROI(roi, SCALE)
            cv2.rectangle(img, roi.top_left(), roi.bot_right(), color, thickness)

    ######################################################

    ######################################################

    def perform_ocr(self, img: ndarray, conf: str):
        try:
            py_result = pytesseract.image_to_string(img,
                                                    config=conf).splitlines()
            self.save_field_data(self.truth_dict, new_txt_array=py_result)
        except:
            print("ERROR performing ocr")

    ######################################################
    def roi_selected(self):
        if not self.coords is None:
            self.current_angle = 0.0
            self.roi = None
            self.inner_rois = []
            self.truth_dict.fields = dict()
            self.unchopped_roi = Rect.new_instance(self.coords).scale(1.0 / SCALE)
            self.coords_roi = self.coords = None
            utx, uty, ubx, uby = self.unchopped_roi.region()
            self.cropped_img = cv2.resize(self.img[uty:uby, utx:ubx], (0, 0), fx=self.scale_var.get(),
                                          fy=self.scale_var.get())
            self.roi = self.unchopped_roi
            self.destroy_window(self.windowROI)
            self.lb.delete(0.0, END)

        self.rotated_mat = self.cropped_img
        angle = perform_osd(self.cropped_img)
        self.rotateROI(angle)
        self.showROIs()
        self.times = []
        self.roi = None

    ######################################################
    def roi_inner_selected(self, conf: str = None):
        if conf is None:
            conf = self.ocr_type.get()
        if not self.coords_roi is None:
            utx, uty, ubx, uby = self.coords_roi.region()
            if self.rotated_mat is None:
                self.cropped_img_inner = self.cropped_img[uty:uby, utx:ubx]
            else:
                self.cropped_img_inner = self.rotated_mat[uty:uby, utx:ubx]
            py_result = pytesseract.image_to_string(self.cropped_img_inner,
                                                    config=conf).splitlines()
        else:
            return
        if len(py_result) == 0:
            return
        self.inner_rois.append(self.coords_roi)
        utx, uty, ubx, uby = self.coords_roi.scale(1 / self.scale_var.get()).region()
        newTX = utx + self.unchopped_roi.x
        newTY = uty + self.unchopped_roi.y
        newBX = ubx + self.unchopped_roi.x
        newBY = uby + self.unchopped_roi.y
        chopped_roi = Rect(newTX, newTY, newBX - newTX, newBY - newTY)
        self.field_tuple = Fields._make(
            ["", "", self.unchopped_roi.to_str(), self.coords_roi.to_str(), self.current_angle])
        self.roi = chopped_roi
        self.showROIs()
        self.save_field_data(self.truth_dict, new_txt_array=py_result)

    ######################################################
    def scale(self, scale: float) -> Rect:
        return Rect(round(scale * self.x), round(scale * self.y), round(scale * self.w), round(scale * self.h))

    ######################################################
    @staticmethod
    def scaleROI(roi: Rect, scale: float) -> Rect:
        return roi.scale(scale)

    ######################################################
    def scaleROIs(self, rois: List[Rect], scale: float) -> List[Rect]:
        if len(rois) > 0:
            return [self.scaleROI(roi, scale) for roi in rois if roi is not None]
        return []

    ######################################################
    def rotateROI(self, angle: float, isNew: bool = False):
        try:
            if not self.windowROI is None:
                self.destroy_window(self.windowROI)
            if not self.current_angle is None:
                self.current_angle += angle
            else:
                self.current_angle = angle

            if not isNew:
                self.inner_rois = []
                self.roi = None

            self.rotated_mat, rotated_pil, mask, _ = self.rotate_image(self.cropped_img, self.current_angle)
            self.pasted_photo, self.pasted_size = self.paste_image(rotated_pil, mask)
            self.showROIs()
        except:
            print("ROTATE ROI ERR")
            traceback.print_exc()
            pass

    ######################################################
    def save_field_data(self, truth_dict: Truth, new_txt_array: List[str] = None):
        if not self.windowROI is None:
            self.destroy_window(self.windowROI)

        new_txt_array.reverse()
        for i, txt in enumerate(new_txt_array):
            if txt.strip() == "":
                continue

            self.lb.insert(END, self.clean_txt(txt) + "\n")

            key = time.time() + i * .001
            self.times.append(key)
            self.field_tuple = Fields._make(
                ["", txt, self.unchopped_roi.to_str(), "", self.current_angle])
            truth_dict.fields[key] = self.field_tuple
        self.lb.see(END)
        self.showROIImg()

    ############################# #########################
    def save_data(self, truth_dict: Truth):
        current_time = time.time()
        truth_id = truth_dict.image_id
        sql_commands = list()

        for i, line in enumerate(self.lb.get(0.0, END).split("\n")):
            if line.strip() == "":
                continue
            line = self.clean_txt(line)
            aTime = time.time() + i * .001
            sql_commands.append(
                [
                    "INSERT INTO FIELDS (truth_id, field_type, txt, add_block_roi, add_line_roi, angle, time) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (truth_id, i, line, self.unchopped_roi.to_str(), self.unchopped_roi.to_str(),
                     str(self.current_angle), aTime)])
        is_unresolvable = ''
        if self.unresolvable_var.get():
            is_unresolvable = 'U'
        if len(sql_commands) > 0 or self.unresolvable_var.get():
            if self.mode == MODES.REVIEWER:
                sql_commands.append(["UPDATE TRUTHS SET istruthed = 2, time = ?, flag = ?  WHERE id = ?",
                                     (current_time, is_unresolvable, truth_id,)])
            else:
                sql_commands.append(["UPDATE TRUTHS SET istruthed = 1, time = ?, flag = ? WHERE id = ?",
                                     (current_time, is_unresolvable, truth_id,)])
        try:
            self.db.executemultiplecommands(sql_commands)
        except Exception:
            messagebox.showwarning("Critical Error", "Truth save error")
            traceback.print_exc()
            return
        self.next_selection(1)

    ######################################################
    def populate_truth_dictionary(self, image_name: str) -> Truth:
        (self.image_id, self.truth_time, flag) = \
        self.db.select("SELECT id,time,flag FROM TRUTHS WHERE image_name = ?", (image_name,))[0]
        self.imageName = image_name
    #    truth_dict[FIELDS] = {}
        fields_rs = self.db.select(
            "SELECT id,field_type,txt,add_block_roi,add_line_roi,angle,time FROM FIELDS WHERE truth_id = ?",
            (self.image_id,))
        truth = Truth(self.image_id, image_name)
        for field in fields_rs:
            (field_id, field_type, txt, add_block_roi, add_line_roi, angle, field_time) = field
            self.lb.insert(END, txt + "\n")
            self.field_tuple = Fields._make([field_type, txt, add_block_roi, add_line_roi, angle])
            truth.fields[field_time] = self.field_tuple
        self.truths[self.image_id] = truth
        if flag == 'U':
            self.unresolvable_var.set(True)
        return truth

    ######################################################

    @staticmethod
    def clean_txt(txt: str):
        txt = re.sub(r'\s*-\s*', '-', txt)
        txt = re.sub(r"\.", '', txt)
        txt = re.sub(r'[^0-9]-', '', txt)
        txt = re.sub(r'-[^0-9]', '', txt)
        txt = re.sub(r'-$', '', txt)
        txt = re.sub(r'([^0-9])/([^0-9])', r"\1 \2", txt)
        txt = re.sub(r'[^ A-Za-z0-9-#/&]', ' ', txt)
        return txt.upper()

    ######################################################

    def populate_data_list(self):
        for i, line in self.truth_data_box.get(0, END).split("\n"):
            self.lb.insert(END, self.clean_txt(line) + "\n")
        self.truth_data_box.see(END)

    ######################################################
    def get_rois_from_truth_dict(self, truth_dict: Truth) -> tuple[list, Rect | None, list[Rect | None]]:
        inner_rois = []
 #       times = []
#        if len(truth_dict.FIELDS) > 0:
        times = list(truth_dict.fields)
        times.sort()
        for aTime in times:
            self.current_angle = truth_dict.fields[aTime].ANGLE
            self.coords = Rect.new_instance(truth_dict.fields[aTime].ADD_BLOCK_ROI)
            self.unchopped_roi = Rect.new_instance(self.coords)
            inner_rois.append(self.coords)
            break
        return times, self.coords, inner_rois

    ######################################################
    def populate_ui(self, truth_dict: Truth, is_new: bool = False):
        if is_new:
            return
        self.imageName = truth_dict.image_name
        self.image_id = truth_dict.image_id
