'''
Created on 03 ott 2016

@author: lorenzocioni
'''
import cv2
import numpy as np
import numpy.linalg as npl
from sklearn import svm, model_selection
import os
from sklearn.externals import joblib
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import accuracy_score
import descriptors
import illuminantMaps
import config
import utils
import math


'''
Splicing detection main procedure. The result of the output
will be a number of regions of the image that can be spliced
over an image
'''
class FaceSplicingDetection:

    def __init__(self, extractMaps, extractFeatures, crossVal, verbose, heatMap):
        self.verbose = verbose
        self.extract_maps = extractMaps
        self.extract_features = extractFeatures
        self.face_cascade = cv2.CascadeClassifier(config.cascadePath)
        self.cross_validation = crossVal
        self.heat_map = heatMap
        
        #Descriptors
        self.descriptors = ['BIC']


    def detectSplice(self, img, heat_map, depth):
        filename = utils.getFilename(img)
        # Extracting image features
        #features = self.processImage(img, False, self.verbose, heat_map)

        # 2. Statistical difference between IIC and GGE maps
        gge_map = cv2.imread(config.maps_folder + filename + '_gge_map.png')
        iic_map = cv2.imread(config.maps_folder + filename + '_iic_map.png')

        return


    '''
    Train model for further splicing detection
    @param images: the list of images filenames
    @param labels: the list of image labels
    '''
    def train(self, images, labels):        
        # Extract image features from each images in training set
        if self.extract_features or self.extract_maps:
            for i in range(len(images)):
                filename = utils.getFilename(images[i])
                print('Processing ' + filename) 
                self.extractIlluminationMaps(images[i])
                #Extract image descriptors and features
                for desc in self.descriptors:
                    self.extractFeatures(images[i], labels[i], descriptor = desc) 
        
                
        
        return

    '''
    Extract feature vector for a selected image
    '''
    def extractSingleFeatures(self, img):
        self.processImage(img, True)

    '''
    Extract image illuminant maps 
    GGE map
    IIC map
    '''
    def extractIlluminationMaps(self, img):
        filename = utils.getFilename(img)
        illuminantMaps.prepareImageIlluminants(img, config.seg_sigma, config.seg_k, config.seg_min_size, config.min_intensity, config.max_intensity, self.verbose)
        if config.illuminantType == 'GGE':
            illuminantMaps.extractGGEMap(img, filename + "_segmented" + config.maps_out_suffix +".png", config.gge_sigma, config.gge_n, config.gge_p, self.verbose)
        elif config.illuminantType == 'IIC':
            illuminantMaps.extractIICMap(img, filename + "_segmented" + config.maps_out_suffix + ".png", self.verbose)


    '''
    Segment current image extracting human faces
    '''
    def extractFaces(self, img, label):
        orig = cv2.imread(img, cv2.COLOR_BGR2GRAY)
        if self.verbose:
            print('Detecting image faces')
        if label is not None:
            faces = []
            for entry in label:
                face = (int(entry[2]), int(entry[4]), int(entry[3]) - int(entry[2]), int(entry[5]) - int(entry[4]))
                faces.append(face)
        else:
            faces = self.face_cascade.detectMultiScale(
                orig,
                scaleFactor = 1.1,
                minNeighbors = 5,
                minSize = (30, 30),
                flags = cv2.CASCADE_SCALE_IMAGE
            )
        if self.verbose:
            print(str(len(faces)) + ' faces detected')
        return faces


    '''
    Builds feature vector given two set of principal
    components
    '''
    def extractFeatures(self, img, label = None, descriptor = "ACC", space = 0, channel = 3):
        filename = utils.getFilename(img)
        map = cv2.imread(config.maps_folder + filename + '_' + config.illuminantType.lower() + '_map.png')
        faces = self.extractFaces(img, label)
        
        #Storing faces extracted from maps
        count = 0
        for (x, y, w, h) in faces:
            face = map[y:y + h, x:x + w]
            path = config.faces_folder + "face-" + config.illuminantType.upper() + "-" + str(count) + ".png"
            cv2.imwrite(path, face)    
            descriptors.extractDescriptor(path, descriptor, space, channel)
            
            #Face label
            if label is not None:
                test = 1
                
            count = count + 1
            
        features = []
        
        first = 0
        while first < len(faces):
            second = first + 1
            while second < len(faces):
                facePairFeature = []
                firstFaceFeat = config.faces_folder + 'face-' + config.illuminantType + '-' + str(first) + "-" + descriptor.lower() + "-desc.txt"
                secondFaceFeat = config.faces_folder + 'face-' + config.illuminantType + '-'  + str(second) + "-" + descriptor.lower() + "-desc.txt"
                print(firstFaceFeat)
                print(secondFaceFeat)
                files = open(firstFaceFeat, "rt")
                files.seek(0)
                temp = files.readline()
                linesf1 = files.readlines()
                files.close()
                for i in linesf1:
                    desc = list(i)
                    cont = 0
                    while (cont < (len(desc) - 1)):
                        print(float(desc[cont]))
                        facePairFeature.append(float(desc[cont]))
                        cont = cont + 1
                    files = open(secondFaceFeat, "rb")
                    files.seek(0)
                    temp = files.readline()
                    linesf2 = files.readlines()
                    files.close()
                    for j in linesf2:
                        desc = list(j)
                        cont = 0
                        while (cont < (len(desc) - 1)):
                            facePairFeature.append(float(desc[cont]))
                            cont = cont + 1
                
                features.append(facePairFeature)
                second = second + 1
            first = first + 1 
            nameFile = config.features_folder + filename + '_' + descriptor.lower() + ".txt"
            files = open(nameFile, "wt")
            files.seek(0)
            for i in features:
                temp = i
                cont = 0
                for j in temp:
                    if (cont == 0):
                        frase = str(j) + " "
                        files.write(frase)
                    else:
                        frase = str(cont) + ":" + str(j) + " "
                        files.write(frase)
                    cont = cont + 1
                files.write("\n")
            files.close()  
        
        print('\tFeatures extracted from ' + str(len(faces)) + ' faces')    
        return features


    '''
    Builds and visualize the heat map in order to visually evaluate difference
    between two different maps. Using OpenCV COLORMAP_JET, red values indicates
    a more significant difference, blue values indicates lower difference.
    '''
    def visualizeHeatMap(self, gge, iic):
        #Splits all the channels
        gge_b, gge_g, gge_r = cv2.split(gge)
        iic_b, iic_g, iic_r = cv2.split(iic)
        #Get maps dimensions
        rows, cols, _ = gge.shape
        #Building heat map
        heat_map = np.sqrt(pow(gge_b[0:rows-1, 0:cols-1] - iic_b[0:rows-1, 0:cols-1], 2) + pow(gge_g[0:rows-1, 0:cols-1] - iic_g[0:rows-1, 0:cols-1], 2) +  pow(gge_r[0:rows-1, 0:cols-1] - iic_r[0:rows-1, 0:cols-1], 2))
        #Recover heat map max value
        max_value = np.ndarray.max(heat_map)
        #Normalization
        heat_map = heat_map / max_value
        heat_map = heat_map * 255
        heat_map = heat_map.astype(np.uint8)
        #Display color map
        color_map = cv2.applyColorMap(heat_map, cv2.COLORMAP_JET)
        cv2.imshow('img', self.resizeImage(color_map, 500))
        cv2.waitKey(0)
            

