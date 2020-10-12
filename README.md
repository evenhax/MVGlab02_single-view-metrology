# 3D Reconstruction Using Vanishing Points From a Single View

###### Tips: If the math formula can't be displayed, you may need a Google extension: [MathJax Plugin for Github](https://www.crx4chrome.com/crx/72309/).

****

### Preprocess

#### choose a simple image which contains 3 mutually vertical planes, and use a simple annotation tool (LABEL ME) to annotate the image.

* annotate several parallel lines in the world on each vertical plane (make sure lines of each plane are vertical to each other). 

<div align=center><img src="image/line.jpg" width=200></div>

* annotate other parallel lines which are not parallel to above lines (make sure lines of each plane are vertical to each other).

<div align=center><img src="image/line'.jpg" width=200></div>

* annotate the common point of plane intersection lines.

<div align=center><img src="image/intersection.jpg" width=200></div>

* annotate regions where 3D points will be displayed.

<div align=center><img src="image/plane.jpg" width=200></div>

****

### Code

#### 1. load LABEL ME json data, and get parallel lines, common point of plane intersection lines, and masks of vertical planes

#### 2. calculate points and lines at infinity from labeled parallel lines

#### 3. according to intersection points of 3 pairs parallel lines which are mutually orthogonal, calculate camera matrix

$$ cos\theta = \frac {v_1^T \omega v_2^T} {\sqrt {v_1^T \omega v_1^T} \sqrt {v_2^T \omega v_2^T}} $$

when $ \theta = 90^\circ $, 

$$ v_1^T \omega v_1^T=0 , \omega = (KK^T)^{-1} $$

#### 4. according to lines at infinity of 3 vertical planes and camera matrix, calculate scene plane orientations (normal vectors)

$$ n=K^Tl_{horiz} $$

#### 5. substitute the common point(suppose projective depth λ=1) of plane intersection lines into plane equations, to calculate distance between each plane and camera center

$$ \tilde X = \tbinom {\frac {\lambda K^{-1} x} {\left\| K^{-1} x \right\|}} {1} $$

$$ \Big( \frac {\lambda K^{-1} l} {\left\| K^{-1} l \right\|} \Big)^T X + d = 0 $$


#### 6. substitute 2D points into corresponding plane equation, to calculate 3D positions for masked image (up to a unknown scale) and then, save as ply file

<div align="center">
    <img src="image/chessboard_3D.png" width="250"/><img src="image/chessboard_3D'.png" width="250"/><img src="image/chessboard_3D''.png" width="250"/>
</div>
