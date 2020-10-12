# -*- coding: utf-8 -*-
"""
3D Reconstruction Using Vanishing Points From a Single View
"""


import json
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np

from labelme import utils
from collections import defaultdict
from scipy.linalg import svd, cholesky, qr


def solution(A):  

    """Solves homogenous linear equations."""

    ## Ax = 0

    # SVD
    u, e, v = svd(A)
    x = v.T[:, -1]  # min column of right singular vector

    """ 
    ## Other Methods
    # find the eigenvalues and eigenvector of A.T * A -- right singular 
    e_vals, e_vecs = np.linalg.eig(np.dot(A.T, A)) 
    # extract the eigenvector (column) associated with the minimum eigenvalue 
    x = np.array(e_vecs[:, np.argmin(np.abs(e_vals))])
    """

    # np.set_printoptions(suppress=True)
    # print(A, x, np.dot(A, x.reshape(4, 1)))

    return x


def get_label(img, data_line, data_plane):

    """Gets parallel lines and vertical planes from label json."""

    ## get parallel lines 
    
    # print(data_line['shapes'])
    line2points = defaultdict(list)  # store 2 points on each parallel line 
    line_names = ["XZ_line", "YZ_line", "XY_line", "XZ_line'", "YZ_line'", "XY_line'",]
    intersect = []  # common point of plane intersection line
    for each_shape in data_line['shapes']:
        for each_line in line_names:
            if each_shape['label'] == each_line:
                # print(each_shape['points'])
                # print([list(reversed(each_shape['points'][0])), list(reversed(each_shape['points'][1]))])
                line2points[each_line].append([list(reversed(each_shape['points'][0])), list(reversed(each_shape['points'][1]))])
            elif each_shape['label'] == "intersection":  # common point of plane intersection line
                intersect = list(reversed(each_shape['points'][0])) + [1]
    # print(line2points)

    ## get vertical planes

    lbl, lbl_names = utils.labelme_shapes_to_label(img.shape, data_plane['shapes']) 

    # lbl：binary array  in: 1  out: 0
    # lbl_names ：dict   _background_：0   other labels: positive
    # print(lbl_names)
    mask = []  #  for 3 verticle planes
    for i in range(1, len(lbl_names)):  # ignore background
        mask.append((lbl == i).astype(np.uint8))  

    # captions = ['%d: %s' % (l, name) for l, name in enumerate(lbl_names)]
    # lbl_viz = utils.draw_label(lbl, img, captions)
    # plt.imshow(lbl_viz)
    # plt.show()

    return line2points, intersect, mask


def cal_vanish(line2points):

    """Calculates vanishing points and horizon lines."""
    
    ## calculate vanishing points
    vanish_points = defaultdict(list)  # for pairs of parallel lines 
    for each_line, points in line2points.items():  # dict
        # print(each_line, len(points))
        line = []  # for each pair of parallel lines, store several line equations
        for each_point in points:  # points array
            # cross product -- calculate line equation
            # line.append(np.cross(each_point[0] + [1], each_point[1] + [1]))  # homogenous coordinates
            line.append(solution(np.array([each_point[0] + [1], each_point[1] + [1]])))
        # print(line)
        # p = np.cross(line[0], line[1])  # homogenous -- up to a scale
        p = solution(np.array(line))    
        vanish_points[each_line] = p / p[-1]
    # print(vanish_points)

    ## calculate vanishing lines
    """
    horizs = np.array([np.cross(vanish_points["XZ_line"], vanish_points["XZ_line'"]), 
                       np.cross(vanish_points["YZ_line"], vanish_points["YZ_line'"]),
                       np.cross(vanish_points["XY_line"], vanish_points["XY_line'"])]).T  
    """
    horizs = np.array([solution(np.array([vanish_points["XZ_line"], vanish_points["XZ_line'"]])), 
                       solution(np.array([vanish_points["YZ_line"], vanish_points["YZ_line'"]])), 
                       solution(np.array([vanish_points["XY_line"], vanish_points["XY_line'"]]))]).T
    # print(horizs)

    return vanish_points, horizs


def calibrate(vanish_points):
    
    """Calibrates the camera (square pixels & no skew).""" 

    # W = [[w1 w2 w4] [w2 w3 w5] [w4 w5 w6]]
    # (square pixels: w2 = 0  no skew: w1 = w3)

    # θ = 90° -- v1.T * W * v2 = 0 ; v2.T * W * v3 = 0 ; v1.T * W * v4 = 0
    # (a1a2 + b1b2)w1 + (c1a2 + a1c2)w4 + (c1b2 + b1c2)w5 + c1c2w6 = 0
    # (a1a3 + b1b3)w1 + (c1a3 + a1c3)w4 + (c1b3 + b1c3)w5 + c1c3w6 = 0
    # (a2a3 + b2b3)w1 + (c2a3 + a2c3)w4 + (c2b3 + b2c3)w5 + c2c3w6 = 0      

    a1, b1, c1 = vanish_points["XZ_line"]
    a2, b2, c2 = vanish_points["YZ_line"]
    a3, b3, c3 = vanish_points["XY_line"]

    param = np.array([[a1 * a2 + b1 * b2, c1 * a2 + a1 * c2, c1 * b2 + b1 * c2, c1 * c2], 
                      [a1 * a3 + b1 * b3, c1 * a3 + a1 * c3, c1 * b3 + b1 * c3, c1 * c3],
                      [a2 * a3 + b2 * b3, c2 * a3 + a2 * c3, c2 * b3 + b2 * c3, c2 * c3]])  # parameter matrix  

    # print(np.linalg.matrix_rank(param))  # rank < 4 -- non-zero solution
    
    w1, w4, w5, w6 = solution(param)  # solve w1, w4, w5, w6 -- up to a scale
    W = np.array([[w1, 0, w4], [0, w1, w5], [w4, w5, w6]])
    W /= W[-1, -1]
    
    ### Once W is calculated, we get camera matrix K: 

    ## Cholesky factorization -- W = (K.inv).T * (K.inv)
    # e_vals, e_vecs = np.linalg.eig(W) 
    # print(e_vals)  # all e_vals > 0 -- positive denifite
    L = cholesky(W, lower=False)  # W = L.T * L, L is upper trianguler matrix 
    K = np.linalg.inv(L)  # K is upper trianguler matrix 
    K /= K[-1][-1]
    # print(K)

    """
    ### Other Methods
    ## directly -- W = (K * K.T).inv
    # K = [[f 0 u0] [0 f v0] [0 0 1]] (square pixels & no skew)
    # K * K.T = [[f^2 + u0^2 u0v0 u0] [u0v0 f^2 + v0^2 v0] [u0 v0 1]]
    W_inv = np.linalg.inv(W) 
    dot = W_inv / W_inv[-1][-1]
    # print(W, W_inv, dot)
    u0 = dot[-1][0]
    v0 = dot[-1][1]
    # assert u0 * v0 == dot[-1][0] * dot[-1][1]
    # assert abs((u0 * u0 - v0 * v0) - (dot[0][0] - dot[1][1])) < 1e-3
    f = np.sqrt(dot[1][1] - v0 * v0)
    K = np.array([[f, 0, u0], [0, f, v0], [0, 0, 1]])
    # print(K)
    """
    
    return K


def cal_3D(K, p_2D_H):

    """Calculates unit 3D pos without taking projective depth into account."""

    p_3D = np.dot(np.linalg.inv(K), p_2D_H)
    p_3D /= np.linalg.norm(p_3D)  # p / || p ||

    return p_3D


def cal_scene(K, horizs, intersect):

    """Calculates scene plane equations."""

    # X_H.T * Pi = 0 (homogenous) -- Pi = (unit_n.T, d).T
    # unit_n.T * X + d = 0

    ## calculate scene plane orientations -- normal vector
    
    # n = K.T * l_horiz
    N = np.dot(K.T, horizs)
    # unit_n = n / || n ||
    unit_N = N / np.linalg.norm(N, axis=0)
    # print(unit_N)

    ## calculate distance between plane and camera center

    # common point of plane intersection lines in 3D 
    # X_H = (λ * K.inv * x / || K.inv * x ||, 1) -- suppose projective depth λ is 1
    intersect_3D = cal_3D(K, intersect).reshape((3,1))
    # print(intersect_3D)
    # intersect_3D_H = np.append(intersect_3D, 1)

    # substitute the common point into plane equations
    D = -1 * np.dot(unit_N.T, intersect_3D)
    # print(D)

    # unit_N.T * X + D = 0 -- X_H * Pi = 0
    Pi = np.concatenate((unit_N, D.T), axis=0)  # (4, 3)

    return Pi


def reconstruction(K, Pi, img, masks):

    """Reconstructs 3D points in masked image for 3 verticle planes."""

    assert img.shape[:-1] == np.array(masks).shape[1:]

    pos = []  # position in 3D
    rgb = []  # pixel in original image
    for axis, each_mask in enumerate(masks):  # plane XZ; YZ; XY
        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                if each_mask[i, j] == 1:
                    # X_H * Pi = 0 -- X * Pi[:-1] + Pi[-1] = 0
                    # X_H = (λ * K.inv * x / || K.inv * x ||, 1) -- solve λ
                    point = cal_3D(K, [i, j, 1]).reshape((3,1))
                    lambd = -Pi[-1, axis] / np.dot(Pi[:-1, axis], point)
                    pos.append(lambd * point)
                    rgb.append(img[i, j])

    return pos, rgb


def create_output(vertices, colors, filename):

    """Creates point cloud file."""

    vertices = np.hstack([np.array(vertices).reshape(-1, 3), np.array(colors).reshape(-1, 3)])
    np.savetxt(filename, vertices, fmt='%f %f %f %d %d %d') 
    ply_header = '''ply\nformat ascii 1.0\nelement vertex %(vert_num)d\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n'''
    with open(filename, 'r+') as f:
        old = f.read()
        f.seek(0)
        f.write(ply_header % dict(vert_num=len(vertices)))
        f.write(old)


def main():

    # load data

    json_file_line = r'chessboard_line.json'  # label the parallel lines
    json_file_plane = r'chessboard_plane.json'  # label the vertical planes
    data_line = json.load(open(json_file_line))
    data_plane = json.load(open(json_file_plane))
    # img = utils.img_b64_to_arr(data_plane['imageData'])  # png: 4 channels
    img = mpimg.imread(r'chessboard.jpg')
    
    # get parallel lines, common point of plane intersection lines, and masks of vertical planes

    line2points, intersect, masks = get_label(img, data_line, data_plane)

    # calculate points and lines at infinity from labeled parallel lines

    vanish_points, vanish_lines = cal_vanish(line2points)

    # according to intersection points of 3 pairs parallel lines which are mutually orthogonal,
    # calculate camera matrix

    K = calibrate(vanish_points)
    
    # according to lines at infinity of 3 vertical planes and camera matrix, 
    # calculate scene plane orientations (normal vectors);
    # substitute the common point(assuming projective depth) of plane intersection lines into plane equations, 
    # calculate distance between each plane and camera center

    Pi = cal_scene(K, vanish_lines, intersect)

    # substituting 2D points into corresponding plane equation,
    # calculate 3D positions for masked image (up to a unknown scale)

    pos, rgb = reconstruction(K, Pi, img, masks)

    # save as ply file

    create_output(pos, rgb, r'chessboard_3D.ply')

if __name__ == "__main__":
    main()
