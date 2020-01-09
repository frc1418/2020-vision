from cv2 import *
import numpy
import math
from enum import Enum

class Contour:
    """
    An OpenCV pipeline generated by GRIP.
    """
    
    def __init__(self):
        """initializes all values to presets or None if need to be set
        """

        self.__hsv_threshold_hue = [80.0, 170.0]
        self.__hsv_threshold_saturation = [0.0, 150.0]
        self.__hsv_threshold_value = [50.0, 255.0]

        self.hsv_threshold_output = None

        self.__find_contours_input = self.hsv_threshold_output
        self.__find_contours_external_only = False

        self.find_contours_output = None


    def process(self, source0):
        """
        Runs the pipeline and sets all outputs to new values.
        """
        # Step HSV_Threshold0:
        self.__hsv_threshold_input = source0
        (self.hsv_threshold_output) = self.__hsv_threshold(self.__hsv_threshold_input, self.__hsv_threshold_hue, self.__hsv_threshold_saturation, self.__hsv_threshold_value)

        # Step Find_Contours0:
        self.__find_contours_input = self.hsv_threshold_output
        (self.find_contours_output) = self.__find_contours(self.__find_contours_input, self.__find_contours_external_only)
 
        area = 0
        i = 0 #location in list of countours that the largest countour is stored
        for cnt in self.find_contours_output:
            area1 = countourArea(cnt)
            if area1 > area:
                area = area1
                i = cnt
        

        #extreme left and right points:
        leftmost = tuple(i[i[:,:,0].argmin()][0])
        rightmost = tuple(i[i[:,:,0].argmax()][0])

        #convex hull around largest contour
        hull = [[]]
        for q in range(len(i)):
    # creating convex hull object for each contour
            hull.append(convexHull(i[q], True))

        print(hull)
        

    @staticmethod
    def __hsv_threshold(input, hue, sat, val):
        """Segment an image based on hue, saturation, and value ranges.
        Args:
            input: A BGR numpy.ndarray.
            hue: A list of two numbers the are the min and max hue.
            sat: A list of two numbers the are the min and max saturation.
            lum: A list of two numbers the are the min and max value.
        Returns:
            A black and white numpy.ndarray.
        """
        out = cvtColor(input, COLOR_BGR2HSV)
        return inRange(out, (hue[0], sat[0], val[0]),  (hue[1], sat[1], val[1]))

    @staticmethod
    def __find_contours(input, external_only):
        """Sets the values of pixels in a binary image to their distance to the nearest black pixel.
        Args:
            input: A numpy.ndarray.
            external_only: A boolean. If true only external contours are found.
        Return:
            A list of numpy.ndarray where each one represents a contour.
        """
        if(external_only):
            mode = RETR_EXTERNAL
        else:
            mode = RETR_LIST
        method = CHAIN_APPROX_SIMPLE
        contours, hierarchy =findContours(input, mode=mode, method=method)
        return contours


processor = Contour()
path = r'/Users/millerr1/Desktop/PurpletestImg1.jpg'
img = imread(path)
processor.process(img)
imgshow('image', img)