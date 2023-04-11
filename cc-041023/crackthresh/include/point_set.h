#ifndef POINT_SET_H
#define POINT_SET_H

#include <Python.h>


class PointSet {

	public:
		PointSet();
		~PointSet();
		bool add(const int x, const int y);
		PyObject* get_x_data();
		PyObject* get_y_data();
		PyObject* get_xy_data();

	private:
		PyObject *pylist_xvec;
		PyObject *pylist_yvec;
		PyObject *pylist_xyvec;

};

#endif

