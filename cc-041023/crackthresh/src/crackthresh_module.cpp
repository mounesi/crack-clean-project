
#define PY_SSIZE_T_CLEAN

#include <stdio.h>
#include <Python.h>

#include "filter.h"
#include "point_set.h"


static PyObject *crackthresh_error;

static PyObject* crackthresh_filter_simple(PyObject *self, PyObject *args) {
	const unsigned char *img;
	Py_ssize_t count;
	int width;
	int height;
	int x_origin;
	int y_origin;
	int thresh;
	// parse and validate args
	if (!PyArg_ParseTuple(args, "y#iiiii", &img, &count, &width, &height, &x_origin, &y_origin, &thresh))
		return NULL;
	if (width < 0) {
		PyErr_SetString(PyExc_ValueError, "invalid argument: width");
		return NULL;
	}
	if (height < 0) {
		PyErr_SetString(PyExc_ValueError, "invalid argument: width");
		return NULL;
	}
	if (count != (width * height)) {
		char msg[256];
		sprintf(msg, "invalid argument: img (len==%ld, width==%d, height==%d)", count, width, height);
		PyErr_SetString(PyExc_ValueError, msg);
		return NULL;
	}
	if ((thresh < 0) || (thresh > 255)) {
		PyErr_SetString(PyExc_ValueError, "invalid argument: thresh");
		return NULL;
	}
	PointSet ptset;
	bool res = filter::filter_simple(&ptset, img, width, height, x_origin, y_origin, thresh);
	if (!res) {
		PyErr_SetString(crackthresh_error, "filter_simple failed");
		return NULL;
	}
	// prepare and return result
	PyObject *xdata = ptset.get_x_data();
	PyObject *ydata = ptset.get_y_data();
	PyObject *xydata = ptset.get_xy_data();
	PyObject *result = Py_BuildValue("OOO", xdata, ydata, xydata);
	// "O" does not increase the reference count, but PointSet will decrease them on destruction, so we increase them here:
	Py_INCREF(xdata);
	Py_INCREF(ydata);
	Py_INCREF(xydata);
	return result;
}

static PyObject* crackthresh_filter_adaptive(PyObject *self, PyObject *args) {
	const unsigned char *img;
	Py_ssize_t count;
	int width;
	int height;
	int x_origin;
	int y_origin;
	float thresh;
	int radius;
	// parse and validate args
	if (!PyArg_ParseTuple(args, "y#iiiifi", &img, &count, &width, &height, &x_origin, &y_origin, &thresh, &radius))
		return NULL;

	if (width < 0) {
		PyErr_SetString(PyExc_ValueError, "invalid argument: width");
		return NULL;
	}
	if (height < 0) {
		PyErr_SetString(PyExc_ValueError, "invalid argument: width");
		return NULL;
	}
	if (count != (width * height)) {
		char msg[256];
		sprintf(msg, "invalid argument: img (len==%ld, width==%d, height==%d)", count, width, height);
		PyErr_SetString(PyExc_ValueError, msg);
		return NULL;
	}
// TEMP commented out to allow for negative values
//	if ((thresh < (float)0) || (thresh > (float)1)) {
//		PyErr_SetString(PyExc_ValueError, "invalid argument: thresh");
//		return NULL;
//	}
	if (radius < 0) {
		PyErr_SetString(PyExc_ValueError, "invalid argument: radius");
		return NULL;
	}
	PointSet ptset;
	bool res = filter::filter_adaptive(&ptset, img, width, height, x_origin, y_origin, thresh, radius);
	if (!res) {
		PyErr_SetString(crackthresh_error, "filter_adaptive failed");
		return NULL;
	}
	// prepare and return result
	PyObject *xdata = ptset.get_x_data();
	PyObject *ydata = ptset.get_y_data();
	PyObject *xydata = ptset.get_xy_data();
	PyObject *result = Py_BuildValue("OOO", xdata, ydata, xydata);
	// "O" does not increase the reference count, but PointSet will decrease them on destruction, so we increase them here:
	Py_INCREF(xdata);
	Py_INCREF(ydata);
	Py_INCREF(xydata);
	return result;
}

static PyMethodDef crackthresh_methods[] = {
	{
		"filter_simple",
		crackthresh_filter_simple,
		METH_VARARGS,
		"TODO: docstring"
	},
	{
		"filter_adaptive",
		crackthresh_filter_adaptive,
		METH_VARARGS,
		"TODO: docstring"
	},
	{
		NULL,
		NULL,
		0,
		NULL
	}
};

static struct PyModuleDef crackthresh_definition = {
	PyModuleDef_HEAD_INIT,
	"crackthresh",
	"TODO: docstring",
	-1,
	crackthresh_methods
};

extern "C" {
// naming significant; also must match the name keyword argument in setup.py's setup() call (?)
PyMODINIT_FUNC PyInit_crackthresh(void) {
	PyObject *m;
	m = PyModule_Create(&crackthresh_definition);
	if (m == NULL)
		return NULL;
	crackthresh_error = PyErr_NewException("crackthresh.error", NULL, NULL);
	Py_INCREF(crackthresh_error);
	PyModule_AddObject(m, "error", crackthresh_error);
	return m;
}
}
