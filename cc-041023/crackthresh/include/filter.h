#ifndef FILTER_H
#define FILTER_H

#include "point_set.h"


namespace filter {

bool filter_simple(PointSet *ptset, const unsigned char *img, int width, int height, int x_origin, int y_origin, int thresh);
bool filter_adaptive(PointSet *ptset, const unsigned char *img, int width, int height, int x_origin, int y_origin, float thresh, int radius);

}

#endif
