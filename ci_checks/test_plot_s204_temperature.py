import numpy as np
import pytest

from plot_s204_temperature import midplane_values, difference


def test_midplane_interpolates_bracketing_planes_instead_of_random_ties():
    centres=np.array([[0,0,-1],[1,0,-1],[0,0,1],[1,0,1]], dtype=float)
    values=np.array([10,20,30,50], dtype=float)
    result,layers=midplane_values(centres,values,np.array([[0,0,0],[1,0,0]]))
    assert result.tolist()==[20,35]
    assert layers==[-1,1]


def test_existing_native_midplane_is_preserved():
    centres=np.array([[0,0,-1],[0,0,0],[0,0,1]], dtype=float)
    result,layers=midplane_values(centres,np.array([10,70,30]),np.array([[0,0,0]]))
    assert result.tolist()==[70]
    assert layers==[0,0]


def test_velocity_change_uses_vector_difference_not_speed_difference():
    a=np.array([[[1,0,0]]],dtype=float)
    b=np.array([[[-1,0,0]]],dtype=float)
    assert difference(a,b).tolist()==[[2]]


def test_temperature_change_keeps_sign():
    assert difference(np.array([[300.]]), np.array([[299.5]])).tolist()==[[-.5]]


def test_slice_outside_native_layers_is_not_extrapolated():
    with pytest.raises(ValueError,match='outside'):
        midplane_values(np.array([[0,0,1],[0,0,2]]),np.array([10,20]),np.array([[0,0,0]]))
