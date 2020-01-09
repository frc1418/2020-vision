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
            area1 = contourArea(cnt)
            if area1 > area:
                area = area1
                i = cnt
        

        #extreme left and right points:
        leftmost = tuple(i[i[:,:,0].argmin()][0])
        rightmost = tuple(i[i[:,:,0].argmax()][0])

        #convex hull around largest contour
        hull = convexHull(i, True, True, True)
    # creating convex hull object for each contour

        print(hull)
        left = 400
        right = 0
        bottom = 0
        for i in hull:
            if i[0][0] < left:
                left = i[0][0]
            if i[0][0] > right:
                right = i[0][0]
            if i[0][1] > bottom:
                bottom = i[0][1]
        
        bRight = 0
        bLeft = 400
        for i in hull:
            if i[0][1] > bottom - 5:
                if i[0][0] < bLeft:
                    bLeft = i[0][0]
                if i[0][0] < right - 5:
                    bRight = i[0][0]
        print(bRight)
        print(bLeft)
        print(left)
        print(right)


    @staticmethod
    def __hsv_threshold(inputt, hue, sat, val):
        """Segment an image based on hue, saturation, and value ranges.
        Args:
            input: A BGR numpy.ndarray.
            hue: A list of two numbers the are the min and max hue.
            sat: A list of two numbers the are the min and max saturation.
            lum: A list of two numbers the are the min and max value.
        Returns:
            A black and white numpy.ndarray.
        """
        out = cvtColor(inputt, COLOR_BGR2HSV)
        return inRange(out, (hue[0], sat[0], val[0]),  (hue[1], sat[1], val[1]))

    @staticmethod
    def __find_contours(inputt, external_only):
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
        contours, hierarchy =findContours(inputt, mode=mode, method=method)
        return contours


processor = Contour()
path = r'/Users/quirozj/Desktop/boppy.jpg'
img = imread(path)
processor.process(img)
imshow('image', img)
