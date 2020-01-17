#!/usr/bin/env python3
try:
    import cscore as cs
    from cscore import CameraServer, VideoSource
    CSCORE = True
except ImportError:
    CSCORE = False

import json
import math
import os
import sys

import cv2
import numpy as np
from networktables import NetworkTables, NetworkTablesInstance
from networktables.util import ntproperty


IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 768


class Pipeline:
    """
    An OpenCV pipeline generated by GRIP.
    """
    
    approx_constant = ntproperty('/vision/approx_constant', 0.01)

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
        contours, points = self.__find_corner_points(source0, self.find_contours_output)
        
        # Contour will be none if a valid contour matching the hexagonal shape was not found
        if contours is None:
            return source0
        contour = contours[0]

        cv2.drawContours(source0, contours, -1, (128, 255, 0), 3)

        M = cv2.moments(contour)
        cx = int(M['m10']/M['m00'])
        cy = int(M['m01']/M['m00'])

        cv2.drawMarker(source0, (cx, cy), (0, 255, 0), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        self.table.putString('moment', f'{cx} , {cy}')

        leftmost = tuple(contour[contour[:,:,0].argmin()][0])
        leftmost = (leftmost[0] - cx, cy - leftmost[1])
        leftmost = (leftmost[0] + cx, cy - leftmost[1])
        cv2.drawMarker(source0, leftmost, (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)

        for point in points:
            cv2.drawMarker(source0, (cx + point[0], cy - point[1]), (255, 0, 0), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)

        # cv2.circle(source0, )
        # cv2.drawContours(source0, [contour], -1, (0, 255, 0), 10)
        
        ret, rvecs, tvecs = self.__find_vecs(points)
        #print(f'{ret=}, {rvecs=}, {tvecs=}')
        # pythagorean_distance = math.sqrt(sum([x**2 for x in tvecs]))
        plane_distance = math.sqrt(sum(x**2 for x in tvecs[1:]))

        rotation_matrix = cv2.Rodrigues(rvecs.ravel())[0]
        if self.isRotationMatrix(rotation_matrix):
            rot = self.rotationMatrixToEulerAngles(rotation_matrix)
            rot = [math.degrees(angle) for angle in rot]
            self.table.putNumber('angle_other', rot[0])
            self.table.putNumber('angle_vertical', rot[1])
            self.table.putNumber('angle_horizontal', rot[2])
        self.table.putNumber('plane_distance', plane_distance)

        return source0
        

    @staticmethod
    def __find_vecs(img_points):
        # top left, top right, bottom right, bottom left
        real_points = np.float32([[-18.345919, 11.913979, 0], [19.9766, 10.6217, 0], [10.8253, -6.25, 0], [-10.07172, -6.051697, 0]])

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

    def __find_corner_points(self, source0, contours):
        # Find largest contour
        if len(contours) == 0:
            return None, None
        contour = max(contours, key=cv2.contourArea)
        

        #extreme left and right points:
        leftmost = tuple(contour[contour[:,:,0].argmin()][0])
        rightmost = tuple(contour[contour[:,:,0].argmax()][0])
        bottommost = tuple(contour[contour[:,:,1].argmax()][0])


        # use contour approximation
        epsilon = self.approx_constant * cv2.arcLength(contour,True)
        approx = cv2.approxPolyDP(contour,epsilon,True)

        if len(approx) > 8 or len(approx) < 7:
            return None, None 

        # Other possible methods of finding corners:
        # cv2.goodFeaturesToTrack
        # cv2.convexHull
        # cv2.convexHull -> cv2.approxPolyDP

        # cv2.drawContours(source0, [approx], -1, (168, 50, 50), 3)

        # corners = cv2.goodFeaturesToTrack(cv2.cvtColor(source0, cv2.COLOR_BGR2GRAY), 4, 0.005, 5, mask=mask)
        # corners = np.int0(corners)
        # cv2.drawContours(source0, [mask], -1, (0, 0, 255))
        # for index, corner in enumerate(corners):
            # cv2.drawMarker(source0, tuple(corner[0]), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
            # cv2.putText(source0, str(index), tuple(corner[0]), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.5, (0, 255, 0), thickness=1)
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
            bottomLeft = closestPoint
            bottomRight = lowestPoint
        else:
            bottomLeft = lowestPoint
            bottomRight = closestPoint

        M = cv2.moments(contour)
        cx = int(M['m10']/M['m00'])
        cy = int(M['m01']/M['m00'])
        # cv2.drawMarker(source0, (cx, cy), (0, 255, 0), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)

        leftmost = (leftmost[0] - cx, cy - leftmost[1])
        rightmost = (rightmost[0] - cx, cy - rightmost[1])
        bottomLeft = (bottomLeft[0] - cx, cy - bottomLeft[1])
        bottomRight = (bottomRight[0] - cx, cy - bottomRight[1])
        
        # cv2.drawMarker(source0, tuple(bottomLeft), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, tuple(bottomRight), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, tuple(leftmost), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)
        # cv2.drawMarker(source0, tuple(rightmost), (0, 0, 255), cv2.MARKER_DIAMOND, markerSize=5, thickness=2)

        # cv2.imshow('Output', source0)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # top left, top right, bottom right, bottom left
        return (contour, approx), (leftmost, rightmost, bottomRight, bottomLeft)

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
        if CSCORE:
            hi, contours, hierarchy = cv2.findContours(source, mode=mode, method=method)
        else:
            contours, hierarchy = cv2.findContours(source, mode=mode, method=method)
        return contours

    # Checks if a matrix is a valid rotation matrix.
    @staticmethod
    def isRotationMatrix(R) :
        Rt = np.transpose(R)
        shouldBeIdentity = np.dot(Rt, R)
        I = np.identity(3, dtype = R.dtype)
        n = np.linalg.norm(I - shouldBeIdentity)
        return n < 1e-6
    
    
    # Calculates rotation matrix to euler angles
    # The result is the same as MATLAB except the order
    # of the euler angles ( x and z are swapped ).
    @staticmethod
    def rotationMatrixToEulerAngles(R) :
    
        assert(Pipeline.isRotationMatrix(R))
        
        sy = math.sqrt(R[0,0] * R[0,0] +  R[1,0] * R[1,0])
        
        singular = sy < 1e-6
    
        if  not singular :
            x = math.atan2(R[2,1] , R[2,2])
            y = math.atan2(-R[2,0], sy)
            z = math.atan2(R[1,0], R[0,0])
        else :
            x = math.atan2(-R[1,2], R[1,1])
            y = math.atan2(-R[2,0], sy)
            z = 0
    
        return np.array([x, y, z])


# As a client to connect to a robot
NetworkTables.initialize(server='roborio-1418-frc.local')
table = NetworkTables.getTable('/')

if CSCORE == False:
    processor = Pipeline(table)
    path = os.path.join(os.path.dirname(sys.modules['__main__'].__file__), r'test_image4.png')
    img = cv2.imread(path)
    processor.process(img)
else:
    #################### FRC VISION PI Image Specific #############
    config_file = "/boot/frc.json"

    class CameraConfig: pass

    team = None
    server = False
    cameraConfigs = []

    def parseError(message):
        """
        Cleanly report config parsing error.
        """
        print("config error in " + config_file + ": " + message, sys.stderr)

    def read_camera_config(config):
        """
        Read single camera configuration.
        """
        cam = CameraConfig()

        # name
        try:
            cam.name = config["name"]
        except KeyError:
            parseError("could not read camera name")
            return False

        # path
        try:
            cam.path = config["path"]
        except KeyError:
            parseError("{}: could not read path".format(cam.name))
            return False

        cam.config = config

        cameraConfigs.append(cam)
        return True

    def read_config():
        """
        Read configuration file.
        """
        global team
        global server

        # parse file
        try:
            with open(config_file, "rt") as f:
                j = json.load(f)
        except OSError as err:
            print("could not open {}: {}".format(config_file, err), sys.stderr)
            return False

        # top level must be an object
        if not isinstance(j, dict):
            parseError("must be JSON object")
            return False

        # team number
        team = 1418

        # ntmode (optional)
        if "ntmode" in j:
            str = j["ntmode"]
            if str.lower() == "client":
                server = False
            elif str.lower() == "server":
                server = True
            else:
                parseError("could not understand ntmode value '{}'".format(str))

        # cameras
        try:
            cameras = j["cameras"]
        except KeyError:
            parseError("could not read cameras")
            return False
        for camera in cameras:
            if not read_camera_config(camera):
                return False

        return True

    def start_camera(config):
        """
        Begin running the camera.
        """
        print("Starting {} on {}".format(config.name, config.path))
        cs = CameraServer.getInstance()
        camera = cs.startAutomaticCapture(name=config.name, path=config.path)

        camera.setConfigJson(json.dumps(config.config))

        return cs, camera


    if __name__ == "__main__":
        if len(sys.argv) >= 2:
            config_file = sys.argv[1]
        # read configuration
        if not read_config():
            sys.exit(1)

        # start NetworkTables and create table instance
        ntinst = NetworkTablesInstance.getDefault()
        table = NetworkTables.getTable("vision")
        if server:
            print("Setting up NetworkTables server")
            ntinst.startServer()
        else:
            print("Setting up NetworkTables client")
            ntinst.startClientTeam(team)

        # start cameras
        cameras = []
        streams = []
        for cameraConfig in cameraConfigs:
            cs, cameraCapture = start_camera(cameraConfig)
            streams.append(cs)
            cameras.append(cameraCapture)
        # Get the first camera
        camera_server = streams[0]
        # Get a CvSink. This will capture images from the camera
        cv_sink = camera_server.getVideo()

        # (optional) Setup a CvSource. This will send images back to the Dashboard
        output_stream = camera_server.putVideo("stream", IMAGE_WIDTH, IMAGE_HEIGHT)
        # Allocating new images is very expensive, always try to preallocate
        img = np.zeros(shape=(IMAGE_HEIGHT, IMAGE_WIDTH, 3), dtype=np.uint8)

        pipeline = Pipeline(table)

        # loop forever
        while True:

            # Tell the CvSink to grab a frame from the camera and put it
            # in the source image.  If there is an error notify the output.
            # TODO: Why can't we just use frame for everything?
            timestamp, img = cv_sink.grabFrame(img)
            frame = img
            if timestamp == 0:
                # Send the output the error.
                output_stream.notifyError(cv_sink.getError());
                # Skip the rest of the current iteration
                continue

            # Process the frame and get the returned image. Should have contours drawn on it, but not working.
            processed_frame = pipeline.process(frame)

            # (optional) send image back to the dashboard
            output_stream.putFrame(processed_frame)
