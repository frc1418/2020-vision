import cv2
import numpy as np
import math
from enum import Enum
import os
import sys
from functools import reduce
from networktables import NetworkTables

class Pipeline:
    """
    An OpenCV pipeline generated by GRIP.
    """
    
    def __init__(self, table):
        """initializes all values to presets or None if need to be set
        """
        self.table = table

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
 
        contour, points = self.__find_corner_points(source0, self.find_contours_output)
        ret, rvecs, tvecs = self.__find_vecs(points)
        print(f'{ret=}, {rvecs=}, {tvecs=}')
        distance = math.sqrt(reduce(lambda x, y: x + (y**2), tvecs, 0))
        print(f'Pythagorean distance: {distance}')
        self.table.putNumber('/vision/distance', distance)
        self.table.putNumber('/vision/angle', 0)

    @staticmethod
    def __find_vecs(img_points):
        # top left, top right, bottom right, bottom left
        real_points = np.float32([[-1.65625, 0.25, 0], [1.65625, 0.25, 0], [0.8177, -1.1, 0], [-0.8177, -1.1, 0]])

        return cv2.solvePnP(
            real_points, np.float32(img_points), 
            np.float64([
                [498.54399231, 0.0, 323.63196758],
                [0.0, 497.25369582, 249.59554532],
                [0.0, 0.0, 1.0]
            ]),  # Camera matrix
            np.float64([
                1.48882516e-01, -1.63106020e-01, 6.02445681e-04,
                1.17833144e-04, -3.89726894e-01
            ])  # Distortion coefficients
        )

    @staticmethod
    def __find_corner_points(source0, contours):
        # Find largest contour
        contour = max(contours, key=cv2.contourArea)
        

        #extreme left and right points:
        leftmost = tuple(contour[contour[:,:,0].argmin()][0])
        rightmost = tuple(contour[contour[:,:,0].argmax()][0])
        bottommost = tuple(contour[contour[:,:,1].argmax()][0])


        # use contour approximation
        epsilon = 0.01*cv2.arcLength(contour,True)
        approx = cv2.approxPolyDP(contour,epsilon,True)
        # cv2.drawContours(source0, [approx], -1, (168, 50, 50), 3)

        # corners = cv2.goodFeaturesToTrack(cv2.cvtColor(source0, cv2.COLOR_BGR2GRAY), 4, 0.005, 5, mask=mask)
        # corners = np.int0(corners)
        # cv2.drawContours(source0, [mask], -1, (0, 0, 255))
        # for index, corner in enumerate(corners):
            # cv2.drawMarker(source0, tuple(corner[0]), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
            # cv2.putText(source0, str(index), tuple(corner[0]), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.5, (0, 255, 0), thickness=1)

        # Find moments

        # M = cv2.moments(contour)
        # cx = int(M['m10']/M['m00'])
        # cy = int(M['m01']/M['m00'])

        # cv2.drawContours(source0, [contour], -1, (0, 255, 0), 2)
        # cv2.drawMarker(source0, tuple(bottomRight), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, tuple(bottomLeft), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, leftmost, (255, 0, 0), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, rightmost, (255, 0, 0), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, (cx, cy), (0, 255, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)

        # Find the bottommost point in the array of approximated vertices
        bottom = 0
        lowestPointLoc = 0
        for index, i in enumerate(approx):
            if i[0][1] > bottom:
                lowestPointLoc = index
                bottom = i[0][1]
        # find the points before and after the bottomost point in the array 
        pointBeforeLoc = lowestPointLoc - 1
        pointAfterLoc = (lowestPointLoc + 1) % len(approx)

        # Use the point closest to the bottom most point on the y-axis
        if approx[pointBeforeLoc][0][1] > approx[pointAfterLoc][0][1]:
            closestPointLoc = pointBeforeLoc
        else:
            closestPointLoc = pointAfterLoc

        closestPoint = approx[closestPointLoc][0]
        lowestPoint = approx[lowestPointLoc][0]
        #find bottomleft and bottomright
        if closestPoint[0] < lowestPoint[0]:
            bottomLeft = (closestPoint[0], closestPoint[1])
            bottomRight = (lowestPoint[0], lowestPoint[1])
        else:
            bottomLeft = (lowestPoint[0], lowestPoint[1])
            bottomRight = (closestPoint[0], closestPoint[1])
        
        # cv2.drawMarker(source0, (bottomLeftX, bottomLeftY), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, (bottomRightX, bottomRightY), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, tuple(leftmost), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, tuple(rightmost), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)

        # cv2.imshow('Output', source0)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # top left, top right, bottom right, bottom left
        return contour, (leftmost, rightmost, bottomRight, bottomLeft)

    @staticmethod
    def __hsv_threshold(source, hue, sat, val):
        """Segment an image based on hue, saturation, and value ranges.
        Args:
            input: A BGR numpy.ndarray.
            hue: A list of two numbers the are the min and max hue.
            sat: A list of two numbers the are the min and max saturation.
            lum: A list of two numbers the are the min and max value.
        Returns:
            A black and white numpy.ndarray.
        """
        out = cv2.cvtColor(source, cv2.COLOR_BGR2HSV)
        return cv2.inRange(out, (hue[0], sat[0], val[0]),  (hue[1], sat[1], val[1]))

    @staticmethod
    def __find_contours(source, external_only):
        """Sets the values of pixels in a binary image to their distance to the nearest black pixel.
        Args:
            input: A numpy.ndarray.
            external_only: A boolean. If true only external contours are found.
        Return:
            A list of numpy.ndarray where each one represents a contour.
        """
        if(external_only):
            mode = cv2.RETR_EXTERNAL
        else:
            mode = cv2.RETR_LIST
        method = cv2.CHAIN_APPROX_SIMPLE
        contours, hierarchy = cv2.findContours(source, mode=mode, method=method)
        return contours


# As a client to connect to a robot
NetworkTables.initialize(server='roborio-1418-frc.local')
table = NetworkTables.getTable('/')

processor = Pipeline(table)
path = os.path.join(os.path.dirname(sys.modules['__main__'].__file__), r'test_image3.jpg')
img = cv2.imread(path)
processor.process(img)