
#include "filter.h"
#include "point_set.h"


namespace filter {

inline int min(int a, int b) {
	return (a < b) ? a : b;
}

inline int max(int a, int b) {
	return (a > b) ? a : b;
}

// returns true on success, else false
bool filter_simple(PointSet *ptset, const unsigned char *img, int width, int height, int x_origin, int y_origin, int thresh) {
	if (width < 0)
		return false;
	if (height < 0)
		return false;
	if ((thresh < 0) || (thresh > 255))
		return false;
	for (int y=0; y<height; ++y)
		for (int x=0; x<width; ++x)
			if (img[(y * width) + x] <= thresh)
				(*ptset).add(x + x_origin, y + y_origin);
	return true;
}

// Bradley/Roth adaptive thresholding
//
// returns true on success, else false
bool filter_adaptive(PointSet *ptset, const unsigned char *img, int width, int height, int x_origin, int y_origin, float thresh, int radius) {
	if (width < 0)
		return false;
	if (height < 0)
		return false;
	if ((thresh < (float)0) || (thresh > (float)1))
		return false;
	if (radius < 0)
		return false;
	// compute integral image
	int img_int[width*height];
	int ysum = 0;
	for (int x=0; x<width; ++x) {
		ysum = 0;
		for (int y=0; y<height; ++y) {
			int idx = (y * width) + x;
			ysum += img[idx];
			img_int[idx] = ysum + ((x > 0) ? img_int[idx - 1] : 0);
		}
	}
	// perform adaptive thresholding
	int num_pix;
	int x1, x2, y1, y2, sum1, sum2, sum3, sum4, sum_rect;
	for (int x=0; x<width; ++x) {
		for (int y=0; y<height; ++y) {
			x1 = filter::max(0,          x - radius);
			x2 = filter::min(width  - 1, x + radius);
			y1 = filter::max(0,          y - radius);
			y2 = filter::min(height - 1, y + radius);
			num_pix = (x2 - x1 + 1) * (y2 - y1 + 1);
			sum1 =                           img_int[((y2    ) * width) + (x2    )]     ;
			sum2 =  (y1 > 0)              ? (img_int[((y1 - 1) * width) + (x2    )]) : 0;
			sum3 =  (x1 > 0)              ? (img_int[((y2    ) * width) + (x1 - 1)]) : 0;
			sum4 = ((x1 > 0) && (y1 > 0)) ? (img_int[((y1 - 1) * width) + (x1 - 1)]) : 0;
			sum_rect = sum1 - sum2 - sum3 + sum4;
			if ((img[(y * width) + x] * (int)num_pix) <= (sum_rect * (((float)1) - thresh)))
				(*ptset).add(x + x_origin, y + y_origin);
		}
	}
	return true;
}

}
