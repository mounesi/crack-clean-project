
#include "point_set.h"


PointSet::PointSet() {
	pylist_xvec = PyList_New(0);
	pylist_yvec = PyList_New(0);
	pylist_xyvec = PyList_New(0);
}

// TODO: check type
bool PointSet::add(const int x, const int y) {
	PyObject *x_py = PyLong_FromLong(x);		//TODO: err check
	PyObject *y_py = PyLong_FromLong(y);		//TODO: err check

	int res;
	res = PyList_Append(pylist_xvec, x_py);
	if (res != 0)
		return false;
	res = PyList_Append(pylist_yvec, y_py);
	if (res != 0)
		return false;
	res = PyList_Append(pylist_xyvec, x_py);
	if (res != 0)
		return false;
	res = PyList_Append(pylist_xyvec, y_py);
	if (res != 0)
		return false;
	Py_DECREF(x_py);
	Py_DECREF(y_py);
	return true;
}

PointSet::~PointSet() {
	Py_DECREF(pylist_xvec);
	Py_DECREF(pylist_yvec);
	Py_DECREF(pylist_xyvec);
}

PyObject* PointSet::get_x_data() {
	return pylist_xvec;
}

PyObject* PointSet::get_y_data() {
	return pylist_yvec;
}

PyObject* PointSet::get_xy_data() {
	return pylist_xyvec;
}

