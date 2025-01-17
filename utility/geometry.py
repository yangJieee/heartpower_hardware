# coding=utf-8

import numpy as np
import math
import scipy.linalg as linalg

"""获取旋转矩阵
Args:
  axis 旋转轴
  radian 旋转角度(单位:弧度)
Returns:
Raises:
"""
def get_rotate_mat(axis: list, radian) -> list:
  rot_matrix = linalg.expm(np.cross(np.eye(3), axis / linalg.norm(axis) * radian))
  return rot_matrix

"""绕Z轴旋转n度
Args:
Returns:
Raises:
"""
def rotate_with_axisZ(deg, p3d:list) -> np.array:
  axis_z = [0, 0, 1] 
  yaw = math.radians(deg)
  #返回旋转矩阵
  rot_matrix = get_rotate_mat(axis_z, yaw)
  return np.dot(rot_matrix, p3d)

"""
/**
 * @brief   Quaterniond To Rotation YPR
 * @param  [in]  Eigen Quaterniond 按照(w x y z ) 方式存储
 * @retval      Rotation ypr Vector3d 按照(Y,P,R)( Z, Y, X ) 方式存储
 *              返回的值范围[ -Pi -- +Pi ] [ -Pi/2 -- +Pi/2 ] [ -Pi -- +Pi ]，适合用来提取航向角
 * @note        Rotation ypr Vector3d 按照(Y,P,R)( Z, Y, X ) 方式存储,即ypr[0]=yaw ypr[1]=pitch ypr[2]=roll
 */
"""
def quaterniond_to_rotationYPR(q: np.array([0,0,0,0], dtype='float64')) -> np.array:
  ans = np.zeros(3, dtype='float64')

  qw = q[0]
  qx = q[1]
  qy = q[2]
  qz = q[3]
  q2sqr = qy * qy
  t0 = -2.0 * (q2sqr + qz * qz) + 1.0
  t1 = +2.0 * (qx * qy + qw * qz)
  t2 = -2.0 * (qx * qz - qw * qy)
  t3 = +2.0 * (qy * qz + qw * qx)
  t4 = -2.0 * (qx * qx + q2sqr) + 1.0

  t2 = 1.0 if(t2 > 1.0) else t2
  t2 = -1.0 if(t2 < -1.0) else t2

  ans[0] = math.atan2(t1, t0);   # yaw
  ans[1] = math.asin(t2);        # pitch
  ans[2] = math.atan2(t3, t4);   # roll

  return ans


